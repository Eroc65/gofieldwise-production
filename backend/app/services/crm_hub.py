"""
CRM Integration Hub Service.
Orchestrates intake capture, connector selection, and handoff routing.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import hashlib
import logging
import os

import httpx
from sqlalchemy.orm import Session

from .crm_adapter import StandardizedIntake, HandoffMethod
from .crm_connectors import (
    HousecallProAdapter, ServiceTitanAdapter, JobberAdapter,
    GoogleCalendarAdapter, GoogleBusinessProfileAdapter, ZapierAdapter,
    ManualHandoffCRMAdapter
)
from .token_crypto import decrypt_secret, encrypt_secret
from ..models.crm_hub import (
    CRMConfiguration, IntakeCapture, CRMHandoff, OnboardingProgress,
    IntegrationHubStatus, CRMProvider, IntegrationMode, HandoffStatus,
    IntakeType
)

logger = logging.getLogger(__name__)


class CRMConnectorRegistry:
    """Registry of CRM connectors."""
    
    _connectors = {
        CRMProvider.HOUSECALL_PRO: HousecallProAdapter,
        CRMProvider.SERVICETITAN: ServiceTitanAdapter,
        CRMProvider.JOBBER: JobberAdapter,
        CRMProvider.GOOGLE_CALENDAR: GoogleCalendarAdapter,
        CRMProvider.GOOGLE_BUSINESS_PROFILE: GoogleBusinessProfileAdapter,
        CRMProvider.ZAPIER: ZapierAdapter,
        CRMProvider.MANUAL: ManualHandoffCRMAdapter,
    }
    
    @classmethod
    def get_adapter(cls, provider: CRMProvider, config_data: Dict[str, Any], 
                   field_mapping: Dict[str, str]):
        """Get adapter instance for provider."""
        adapter_class = cls._connectors.get(provider)
        if not adapter_class:
            logger.error(f"Unknown CRM provider: {provider}")
            return None
        return adapter_class(config_data, field_mapping)
    
    @classmethod
    def list_providers(cls) -> List[CRMProvider]:
        """List all supported providers."""
        return list(cls._connectors.keys())


class IntakeProcessor:
    """Process and normalize intakes from various sources."""
    
    @staticmethod
    def process_phone_call(caller_name: str, caller_phone: str, 
                          service_type: str, description: str = None,
                          urgency: str = "medium", 
                          email: str = None,
                          address: str = None,
                          preferred_time: datetime = None,
                          extra_fields: Dict[str, Any] = None) -> StandardizedIntake:
        """
        Process incoming phone call data into standardized format.
        """
        return StandardizedIntake(
            caller_name=caller_name,
            caller_phone=caller_phone,
            caller_email=email,
            caller_address=address,
            service_type=service_type,
            service_description=description,
            urgency_level=urgency,
            preferred_time=preferred_time,
            intake_type="incoming_call",
            source="phone",
            extra_fields=extra_fields or {},
        )
    
    @staticmethod
    def process_web_form(form_data: Dict[str, Any]) -> StandardizedIntake:
        """Process web form submission."""
        return StandardizedIntake(
            caller_name=form_data.get("name"),
            caller_phone=form_data.get("phone"),
            caller_email=form_data.get("email"),
            caller_address=form_data.get("address"),
            service_type=form_data.get("service_type"),
            service_description=form_data.get("description"),
            urgency_level=form_data.get("urgency", "medium"),
            preferred_time=form_data.get("preferred_time"),
            intake_type="form_submission",
            source="web_form",
            extra_fields={k: v for k, v in form_data.items() 
                         if k not in ["name", "phone", "email", "address", 
                                     "service_type", "description", "urgency", 
                                     "preferred_time"]},
        )
    
    @staticmethod
    def process_chat(chat_transcript: str, extracted_data: Dict[str, Any]) -> StandardizedIntake:
        """Process chat conversation."""
        return StandardizedIntake(
            caller_name=extracted_data.get("name"),
            caller_phone=extracted_data.get("phone"),
            caller_email=extracted_data.get("email"),
            service_type=extracted_data.get("service_type"),
            service_description=extracted_data.get("description"),
            urgency_level=extracted_data.get("urgency", "medium"),
            intake_type="chat",
            source="chat_system",
            extra_fields={"transcript": chat_transcript},
        )


class CRMIntegrationHub:
    """Main service orchestrating CRM integrations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.registry = CRMConnectorRegistry
    
    # ========================================================================
    # CONFIGURATION MANAGEMENT
    # ========================================================================
    
    def create_crm_config(self, 
                         org_id: int,
                         crm_provider: CRMProvider,
                         integration_mode: IntegrationMode,
                         name: str,
                         config_data: Dict[str, Any],
                         field_mapping: Dict[str, str]) -> Optional[CRMConfiguration]:
        """Create new CRM configuration."""
        try:
            if crm_provider == CRMProvider.JOBBER:
                ok, message = self._validate_jobber_field_mapping(field_mapping)
                if not ok:
                    logger.warning(f"Jobber config rejected: {message}")
                    return None
                config_data = dict(config_data or {})
                if config_data.get("access_token"):
                    config_data["access_token"] = encrypt_secret(config_data.get("access_token"))
                if config_data.get("refresh_token"):
                    config_data["refresh_token"] = encrypt_secret(config_data.get("refresh_token"))

            config = CRMConfiguration(
                organization_id=org_id,
                crm_provider=crm_provider,
                integration_mode=integration_mode,
                name=name,
                config_data=config_data,
                field_mapping=field_mapping,
                is_active=False,  # Starts inactive until tested
                handoff_status=HandoffStatus.PENDING_SETUP,
                requires_approval=True,
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            
            logger.info(f"Created CRM config: {name} ({crm_provider}) for org {org_id}")
            
            # Track onboarding
            self._update_onboarding_progress(org_id, config.id, step=2)
            
            return config
        except Exception as e:
            logger.error(f"Failed to create CRM config: {str(e)}")
            self.db.rollback()
            return None

    def _validate_jobber_field_mapping(self, field_mapping: Dict[str, str]) -> Tuple[bool, str]:
        """
        Validate the Jobber mapping contract.
        The keys are canonical intake fields and values are non-empty Jobber targets.
        """
        required_keys = ["caller_name", "caller_phone", "service_type"]
        missing = [key for key in required_keys if not str(field_mapping.get(key, "")).strip()]
        if missing:
            return False, f"Missing required Jobber field mappings: {', '.join(missing)}"
        return True, "ok"

    async def ensure_jobber_access_token(self, config: CRMConfiguration) -> Tuple[bool, str]:
        """
        Ensure Jobber config has a usable access token.
        Refreshes token when expired (or near expiry) using refresh token.
        """
        if config.crm_provider != CRMProvider.JOBBER:
            return True, "not_jobber"

        config_data = dict(config.config_data or {})
        access_token = decrypt_secret(config_data.get("access_token"))
        refresh_token = decrypt_secret(config_data.get("refresh_token"))
        expires_at_raw = config_data.get("expires_at")

        if not access_token and not refresh_token:
            return False, "Jobber OAuth tokens are not configured"

        is_expired = False
        if expires_at_raw:
            try:
                expires_at = datetime.fromisoformat(str(expires_at_raw).replace("Z", "+00:00"))
                # 2-minute safety buffer
                is_expired = (expires_at.timestamp() - datetime.utcnow().timestamp()) <= 120
            except ValueError:
                is_expired = True
        else:
            is_expired = not bool(access_token)

        if not is_expired and access_token:
            return True, "token_valid"

        if not refresh_token:
            return False, "Jobber access token expired and no refresh token is available"

        client_id = os.getenv("JOBBER_CLIENT_ID", "").strip()
        client_secret = os.getenv("JOBBER_CLIENT_SECRET", "").strip()
        token_url = os.getenv("JOBBER_TOKEN_URL", "https://api.getjobber.com/api/oauth/token").strip()
        if not client_id or not client_secret:
            return False, "JOBBER_CLIENT_ID/JOBBER_CLIENT_SECRET must be set to refresh token"

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(token_url, json=payload)
            if response.status_code >= 400:
                return False, f"Jobber token refresh failed ({response.status_code})"
            token_data = response.json()
        except Exception as exc:
            return False, f"Jobber token refresh request failed: {exc}"

        new_access = token_data.get("access_token")
        new_refresh = token_data.get("refresh_token") or refresh_token
        expires_in = int(token_data.get("expires_in") or 3600)
        if not new_access:
            return False, "Jobber token refresh returned no access_token"

        new_expires_at = datetime.utcfromtimestamp(datetime.utcnow().timestamp() + expires_in).isoformat() + "Z"
        config_data["access_token"] = encrypt_secret(new_access)
        config_data["refresh_token"] = encrypt_secret(new_refresh)
        config_data["expires_at"] = new_expires_at
        config.config_data = config_data
        self.db.commit()
        self.db.refresh(config)
        return True, "token_refreshed"

    def _build_jobber_idempotency_key(self, intake_id: int, org_id: int, config_id: int) -> str:
        raw = f"jobber:{org_id}:{config_id}:{intake_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _decrypted_jobber_config_data(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(config_data or {})
        if "access_token" in data:
            data["access_token"] = decrypt_secret(data.get("access_token"))
        if "refresh_token" in data:
            data["refresh_token"] = decrypt_secret(data.get("refresh_token"))
        return data

    async def refresh_expiring_jobber_tokens(self, threshold_seconds: int = 900) -> Dict[str, int]:
        checked = 0
        refreshed = 0
        failed = 0
        now_ts = datetime.utcnow().timestamp()
        configs = self.db.query(CRMConfiguration).filter(
            CRMConfiguration.crm_provider == CRMProvider.JOBBER,
        ).all()
        for config in configs:
            checked += 1
            config_data = dict(config.config_data or {})
            expires_at_raw = config_data.get("expires_at")
            if not expires_at_raw:
                continue
            try:
                expires_at = datetime.fromisoformat(str(expires_at_raw).replace("Z", "+00:00")).timestamp()
            except ValueError:
                expires_at = now_ts
            if (expires_at - now_ts) > threshold_seconds:
                continue
            ok, _msg = await self.ensure_jobber_access_token(config)
            if ok:
                refreshed += 1
            else:
                failed += 1
        return {"checked": checked, "refreshed": refreshed, "failed": failed}
    
    def get_crm_config(self, config_id: int, org_id: int) -> Optional[CRMConfiguration]:
        """Get CRM config by ID (org-scoped)."""
        return self.db.query(CRMConfiguration).filter(
            CRMConfiguration.id == config_id,
            CRMConfiguration.organization_id == org_id
        ).first()
    
    def list_crm_configs(self, org_id: int) -> List[CRMConfiguration]:
        """List all CRM configs for organization."""
        return self.db.query(CRMConfiguration).filter(
            CRMConfiguration.organization_id == org_id
        ).all()
    
    def get_active_crm_config(self, org_id: int) -> Optional[CRMConfiguration]:
        """Get primary active CRM config for organization."""
        return self.db.query(CRMConfiguration).filter(
            CRMConfiguration.organization_id == org_id,
            CRMConfiguration.is_active == True,
            CRMConfiguration.handoff_status == HandoffStatus.LIVE
        ).first()
    
    # ========================================================================
    # INTAKE CAPTURE
    # ========================================================================
    
    def capture_intake(self, 
                      org_id: int,
                      intake: StandardizedIntake,
                      intake_type: IntakeType,
                      source: str) -> Optional[IntakeCapture]:
        """Capture and store standardized intake."""
        try:
            # Find missing fields for active config
            active_config = self.get_active_crm_config(org_id)
            missing_fields = []
            
            if active_config:
                adapter = self.registry.get_adapter(
                    active_config.crm_provider,
                    active_config.config_data,
                    active_config.field_mapping
                )
                if adapter:
                    required = adapter.get_required_fields()
                    missing_fields = intake.missing_fields(required)
            
            # Store intake
            db_intake = IntakeCapture(
                organization_id=org_id,
                crm_config_id=active_config.id if active_config else None,
                intake_type=intake_type,
                source=source,
                intake_timestamp=intake.captured_at,
                caller_name=intake.caller_name,
                caller_phone=intake.caller_phone,
                caller_email=intake.caller_email,
                caller_address=intake.caller_address,
                service_type=intake.service_type,
                service_description=intake.service_description,
                urgency_level=intake.urgency_level,
                preferred_time=intake.preferred_time,
                extracted_fields=intake.extra_fields,
                missing_fields=missing_fields,
                ai_confidence=intake.confidence_score,
            )
            
            self.db.add(db_intake)
            self.db.commit()
            self.db.refresh(db_intake)
            
            logger.info(f"Captured intake: {db_intake.id} for org {org_id}")
            
            return db_intake
        except Exception as e:
            logger.error(f"Failed to capture intake: {str(e)}")
            self.db.rollback()
            return None
    
    # ========================================================================
    # HANDOFF ROUTING
    # ========================================================================
    
    async def handoff_to_crm(self, intake_id: int, org_id: int) -> Optional[CRMHandoff]:
        """
        Route intake to appropriate CRM system.
        Handles fallback routing if primary fails.
        """
        try:
            # Get intake
            intake_db = self.db.query(IntakeCapture).filter(
                IntakeCapture.id == intake_id,
                IntakeCapture.organization_id == org_id
            ).first()
            
            if not intake_db:
                logger.error(f"Intake not found: {intake_id}")
                return None
            
            # Get active CRM config
            crm_config = intake_db.crm_config
            if not crm_config or not crm_config.is_active:
                logger.warning(f"No active CRM config for intake {intake_id}")
                return None

            if crm_config.crm_provider == CRMProvider.JOBBER:
                ok, msg = self._validate_jobber_field_mapping(crm_config.field_mapping or {})
                if not ok:
                    logger.error(f"Jobber config mapping invalid: {msg}")
                    return None
                ok, msg = await self.ensure_jobber_access_token(crm_config)
                if not ok:
                    logger.error(f"Jobber token unavailable: {msg}")
                    return None
                existing_success = self.db.query(CRMHandoff).filter(
                    CRMHandoff.organization_id == org_id,
                    CRMHandoff.intake_id == intake_id,
                    CRMHandoff.crm_config_id == crm_config.id,
                    CRMHandoff.is_successful == True,
                ).order_by(CRMHandoff.sent_at.desc()).first()
                if existing_success:
                    logger.info(
                        "Jobber handoff idempotent hit: org=%s intake=%s config=%s handoff=%s",
                        org_id,
                        intake_id,
                        crm_config.id,
                        existing_success.id,
                    )
                    return existing_success
            
            # Convert to standardized intake
            intake = StandardizedIntake(
                caller_name=intake_db.caller_name,
                caller_phone=intake_db.caller_phone,
                caller_email=intake_db.caller_email,
                caller_address=intake_db.caller_address,
                service_type=intake_db.service_type,
                service_description=intake_db.service_description,
                urgency_level=intake_db.urgency_level,
                preferred_time=intake_db.preferred_time,
                extra_fields=intake_db.extracted_fields or {},
            )
            if crm_config.crm_provider == CRMProvider.JOBBER:
                intake.extra_fields["idempotency_key"] = self._build_jobber_idempotency_key(
                    intake_id=intake_id,
                    org_id=org_id,
                    config_id=crm_config.id,
                )
            
            # Get adapter
            adapter = self.registry.get_adapter(
                crm_config.crm_provider,
                self._decrypted_jobber_config_data(crm_config.config_data)
                if crm_config.crm_provider == CRMProvider.JOBBER
                else crm_config.config_data,
                crm_config.field_mapping
            )
            
            if not adapter:
                logger.error(f"Could not create adapter for {crm_config.crm_provider}")
                return None
            
            # Send to CRM
            result = await adapter.send_intake(intake)
            
            # Log handoff
            handoff = CRMHandoff(
                organization_id=org_id,
                intake_id=intake_id,
                crm_config_id=crm_config.id,
                crm_provider=crm_config.crm_provider,
                integration_mode=crm_config.integration_mode,
                crm_payload=result.payload_sent,
                crm_response=result.response_received,
                external_record_id=result.external_record_id,
                external_record_url=result.external_record_url,
                is_successful=result.success,
                error_message=result.error_message,
                handoff_method=result.method.value,
                handled_by="system" if result.method == HandoffMethod.API else result.method.value,
            )
            
            self.db.add(handoff)
            
            # Update intake
            intake_db.is_processed = True
            if result.warnings:
                intake_db.processing_error = "; ".join(result.warnings)
            
            # Update CRM config stats
            crm_config.last_sync_at = datetime.utcnow()
            if result.success:
                crm_config.leads_synced_count += 1
                crm_config.last_sync_error = None
            else:
                crm_config.last_sync_error = result.error_message
            
            self.db.commit()
            self.db.refresh(handoff)
            
            logger.info(f"Handoff completed: {handoff.id}, success={result.success}")
            
            return handoff
        
        except Exception as e:
            logger.error(f"Handoff failed: {str(e)}", exc_info=True)
            self.db.rollback()
            return None
    
    # ========================================================================
    # TEST LEAD
    # ========================================================================
    
    async def run_test_lead(self, config_id: int, org_id: int, 
                           test_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Run test lead to verify CRM integration is working.
        """
        try:
            config = self.get_crm_config(config_id, org_id)
            if not config:
                return False, "CRM config not found"

            if config.crm_provider == CRMProvider.JOBBER:
                ok, msg = self._validate_jobber_field_mapping(config.field_mapping or {})
                if not ok:
                    return False, msg
                ok, msg = await self.ensure_jobber_access_token(config)
                if not ok:
                    return False, msg
            
            # Create test intake
            test_intake = StandardizedIntake(
                caller_name=test_data.get("caller_name", "Test Lead"),
                caller_phone=test_data.get("caller_phone", "555-0000"),
                caller_email=test_data.get("caller_email", "test@example.com"),
                service_type=test_data.get("service_type", "Test Service"),
                service_description="Test lead for integration validation",
                urgency_level="medium",
            )
            
            # Get adapter
            adapter = self.registry.get_adapter(
                config.crm_provider,
                self._decrypted_jobber_config_data(config.config_data)
                if config.crm_provider == CRMProvider.JOBBER
                else config.config_data,
                config.field_mapping
            )
            
            if not adapter:
                return False, "Could not create adapter"
            
            # Send test lead
            result = await adapter.send_intake(test_intake)
            
            # Update config
            config.last_test_at = datetime.utcnow()
            config.last_test_status = "success" if result.success else "failed"
            config.test_lead_count += 1
            
            self.db.commit()
            
            if result.success:
                return True, f"Test successful. External ID: {result.external_record_id}"
            else:
                return False, f"Test failed: {result.error_message}"
        
        except Exception as e:
            logger.error(f"Test lead failed: {str(e)}")
            return False, str(e)
    
    # ========================================================================
    # APPROVAL WORKFLOW
    # ========================================================================
    
    def approve_crm_config(self, config_id: int, org_id: int, 
                          user_id: int) -> Optional[CRMConfiguration]:
        """Approve CRM config to go live."""
        try:
            config = self.get_crm_config(config_id, org_id)
            if not config:
                return None
            
            config.is_active = True
            config.handoff_status = HandoffStatus.LIVE
            config.approved_by_user_id = user_id
            config.approved_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(config)
            
            logger.info(f"Approved CRM config {config_id} for org {org_id}")
            self._update_onboarding_progress(org_id, config_id, step=7)
            
            return config
        except Exception as e:
            logger.error(f"Failed to approve config: {str(e)}")
            self.db.rollback()
            return None
    
    # ========================================================================
    # ONBOARDING TRACKING
    # ========================================================================
    
    def _update_onboarding_progress(self, org_id: int, config_id: int = None, 
                                   step: int = None) -> None:
        """Update onboarding progress."""
        try:
            progress = self.db.query(OnboardingProgress).filter(
                OnboardingProgress.organization_id == org_id
            ).first()
            
            if not progress:
                progress = OnboardingProgress(
                    organization_id=org_id,
                    crm_config_id=config_id,
                )
                self.db.add(progress)
            
            # Update steps
            steps_map = {
                1: "step_1_crm_selected",
                2: "step_2_integration_mode",
                3: "step_3_credentials_provided",
                4: "step_4_field_mapping",
                5: "step_5_test_lead",
                6: "step_6_approved",
                7: "step_7_live",
            }
            
            if step and step in steps_map:
                setattr(progress, steps_map[step], True)
                progress.current_step = step
            
            if config_id:
                progress.crm_config_id = config_id
            
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update onboarding: {str(e)}")
            self.db.rollback()
    
    # ========================================================================
    # STATUS & REPORTING
    # ========================================================================
    
    def get_hub_status(self, org_id: int) -> Optional[IntegrationHubStatus]:
        """Get integration hub status for organization."""
        try:
            status = self.db.query(IntegrationHubStatus).filter(
                IntegrationHubStatus.organization_id == org_id
            ).first()
            
            if not status:
                status = IntegrationHubStatus(organization_id=org_id)
                self.db.add(status)
            
            # Update metrics
            configs = self.db.query(CRMConfiguration).filter(
                CRMConfiguration.organization_id == org_id
            ).all()
            
            intakes = self.db.query(IntakeCapture).filter(
                IntakeCapture.organization_id == org_id
            ).all()
            
            handoffs = self.db.query(CRMHandoff).filter(
                CRMHandoff.organization_id == org_id
            ).all()
            
            status.total_crm_configs = len(configs)
            status.active_configs = len([c for c in configs if c.is_active])
            status.total_intakes_captured = len(intakes)
            status.total_handoffs = len(handoffs)
            status.successful_handoffs = len([h for h in handoffs if h.is_successful])
            status.failed_handoffs = len([h for h in handoffs if not h.is_successful])
            
            if intakes:
                status.last_intake_at = max(i.intake_timestamp for i in intakes)
            if handoffs:
                status.last_handoff_at = max(h.sent_at for h in handoffs)
                failed = [h for h in handoffs if not h.is_successful]
                if failed:
                    latest_failed = max(failed, key=lambda h: h.sent_at)
                    status.last_error_at = latest_failed.sent_at
                    status.last_error_message = latest_failed.error_message
            
            self.db.commit()
            return status
        except Exception as e:
            logger.error(f"Failed to get hub status: {str(e)}")
            return None


# Global singleton
_hub_instance = None


def get_hub(db: Session) -> CRMIntegrationHub:
    """Get CRM integration hub instance."""
    global _hub_instance
    if _hub_instance is None:
        _hub_instance = CRMIntegrationHub(db)
    return _hub_instance
