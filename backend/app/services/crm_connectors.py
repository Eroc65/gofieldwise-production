"""
CRM Provider Connectors.
Implementations for Housecall Pro, ServiceTitan, Jobber, Google Calendar, Google Business Profile.
"""

from typing import Tuple, Dict, Any, List, Optional
import logging
from .crm_adapter import (
    BaseCRMAdapter, APIBasedCRMAdapter, WebhookBasedCRMAdapter, ManualHandoffCRMAdapter,
    StandardizedIntake, HandoffResult, HandoffMethod
)

logger = logging.getLogger(__name__)


# ============================================================================
# HOUSECALL PRO CONNECTOR
# ============================================================================

class HousecallProAdapter(APIBasedCRMAdapter):
    """
    Housecall Pro integration.
    Requires: API key, Max plan (per Housecall Pro docs)
    API: REST API for customers and jobs
    """
    
    BASE_URL = "https://api.housecallpro.com/v1"
    
    def get_name(self) -> str:
        return "Housecall Pro"
    
    def validate_credentials(self) -> Tuple[bool, str]:
        """Verify API key is valid."""
        api_key = self.config_data.get("api_key")
        if not api_key:
            return False, "API key not configured"
        
        # In production, make test API call
        return True, "API key configured"
    
    def get_required_fields(self) -> List[str]:
        return ["caller_name", "caller_phone", "service_type"]
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Housecall Pro uses API key in header."""
        api_key = self.config_data.get("api_key")
        return {"Authorization": f"Key {api_key}"} if api_key else {}
    
    async def send_intake(self, intake: StandardizedIntake) -> HandoffResult:
        """
        Send intake to Housecall Pro.
        Housecall Pro flow:
        1. Create customer (if new)
        2. Create job/service call
        3. Optionally assign to technician
        """
        try:
            # Step 1: Get or create customer
            customer_data = {
                "name": intake.caller_name,
                "phone": intake.caller_phone,
                "email": intake.caller_email,
                "address": intake.caller_address,
            }
            
            # Clean up null values
            customer_data = {k: v for k, v in customer_data.items() if v}
            
            success, response = await self.api_request(
                "POST",
                f"{self.BASE_URL}/customers",
                json=customer_data
            )
            
            if not success:
                logger.warning(f"Failed to create/get customer: {response}")
                # Try fallback to webhook
                return await self._send_via_fallback(intake)
            
            customer_id = response.get("id")
            
            # Step 2: Create job
            job_data = {
                "customerId": customer_id,
                "title": intake.service_type or "Service Call",
                "description": intake.service_description,
                "priority": self._map_urgency_to_priority(intake.urgency_level),
                "dueDate": intake.preferred_time.isoformat() if intake.preferred_time else None,
            }
            
            job_data = {k: v for k, v in job_data.items() if v}
            
            success, response = await self.api_request(
                "POST",
                f"{self.BASE_URL}/jobs",
                json=job_data
            )
            
            if success:
                return HandoffResult(
                    success=True,
                    method=HandoffMethod.API,
                    external_record_id=response.get("id"),
                    external_record_url=f"https://app.housecallpro.com/jobs/{response.get('id')}",
                    payload_sent={"customer": customer_data, "job": job_data},
                    response_received=response,
                )
            else:
                return await self._send_via_fallback(intake)
        
        except Exception as e:
            logger.error(f"Housecall Pro handoff error: {str(e)}")
            return HandoffResult(
                success=False,
                method=HandoffMethod.API,
                error_message=str(e),
                retry_able=True,
            )
    
    async def _send_via_fallback(self, intake: StandardizedIntake) -> HandoffResult:
        """Fallback to webhook if API fails."""
        webhook_url = self.config_data.get("fallback_webhook_url")
        if webhook_url:
            payload = await self._create_fallback_payload(intake)
            import httpx
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(webhook_url, json=payload)
                    response.raise_for_status()
                return HandoffResult(
                    success=True,
                    method=HandoffMethod.WEBHOOK,
                    payload_sent=payload,
                    warnings=["Sent via webhook fallback (API failed)"],
                )
            except Exception as e:
                logger.error(f"Webhook fallback failed: {str(e)}")
        
        return HandoffResult(
            success=False,
            method=HandoffMethod.API,
            error_message="API failed and no webhook fallback configured",
            retry_able=True,
        )
    
    def _map_urgency_to_priority(self, urgency: Optional[str]) -> str:
        """Map urgency level to Housecall priority."""
        mapping = {
            "high": "urgent",
            "medium": "normal",
            "low": "low",
        }
        return mapping.get(urgency, "normal")


# ============================================================================
# SERVICETITAN CONNECTOR
# ============================================================================

class ServiceTitanAdapter(APIBasedCRMAdapter):
    """
    ServiceTitan integration.
    Requires: OAuth/client credentials, app key, tenant ID, client ID/secret
    API: REST/GraphQL API for customers and jobs
    """
    
    BASE_URL = "https://api.servicetitan.com"
    
    def get_name(self) -> str:
        return "ServiceTitan"
    
    def validate_credentials(self) -> Tuple[bool, str]:
        """Verify OAuth token or credentials are valid."""
        required = ["access_token", "tenant_id", "app_key"]
        missing = [k for k in required if not self.config_data.get(k)]
        
        if missing:
            return False, f"Missing required credentials: {', '.join(missing)}"
        
        return True, "Credentials configured"
    
    def get_required_fields(self) -> List[str]:
        return ["caller_name", "caller_phone", "service_type"]
    
    def get_auth_headers(self) -> Dict[str, str]:
        """ServiceTitan uses Bearer token + custom headers."""
        token = self.config_data.get("access_token")
        return {
            "Authorization": f"Bearer {token}",
            "X-App-Key": self.config_data.get("app_key", ""),
        } if token else {}
    
    async def send_intake(self, intake: StandardizedIntake) -> HandoffResult:
        """
        Send intake to ServiceTitan.
        ServiceTitan flow:
        1. Create or find customer
        2. Create job
        """
        try:
            tenant_id = self.config_data.get("tenant_id")
            
            # Step 1: Create customer
            customer_data = {
                "firstName": intake.caller_name or "Unknown",
                "phone": intake.caller_phone,
                "email": intake.caller_email,
                "address": intake.caller_address,
            }
            
            customer_data = {k: v for k, v in customer_data.items() if v}
            
            success, response = await self.api_request(
                "POST",
                f"{self.BASE_URL}/v2/{tenant_id}/crm/customers",
                json=customer_data
            )
            
            if not success:
                logger.warning(f"ServiceTitan customer creation failed: {response}")
                return await self._send_via_fallback(intake)
            
            customer_id = response.get("id")
            
            # Step 2: Create job
            job_data = {
                "customerId": customer_id,
                "name": intake.service_type or "Service Call",
                "description": intake.service_description,
                "priority": self._map_urgency_to_priority(intake.urgency_level),
            }
            
            success, response = await self.api_request(
                "POST",
                f"{self.BASE_URL}/v2/{tenant_id}/crm/jobs",
                json=job_data
            )
            
            if success:
                return HandoffResult(
                    success=True,
                    method=HandoffMethod.API,
                    external_record_id=response.get("id"),
                    payload_sent={"customer": customer_data, "job": job_data},
                    response_received=response,
                )
            else:
                return await self._send_via_fallback(intake)
        
        except Exception as e:
            logger.error(f"ServiceTitan handoff error: {str(e)}")
            return HandoffResult(
                success=False,
                method=HandoffMethod.API,
                error_message=str(e),
                retry_able=True,
            )
    
    async def _send_via_fallback(self, intake: StandardizedIntake) -> HandoffResult:
        """Fallback to Zapier/webhook."""
        webhook_url = self.config_data.get("zapier_webhook_url")
        if not webhook_url:
            return HandoffResult(
                success=False,
                method=HandoffMethod.API,
                error_message="API failed and no Zapier webhook configured",
                retry_able=True,
            )
        
        payload = await self._create_fallback_payload(intake)
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
            return HandoffResult(
                success=True,
                method=HandoffMethod.ZAPIER,
                payload_sent=payload,
                warnings=["Sent via Zapier fallback"],
            )
        except Exception as e:
            logger.error(f"Zapier fallback failed: {str(e)}")
            return HandoffResult(
                success=False,
                method=HandoffMethod.ZAPIER,
                error_message=str(e),
                retry_able=True,
            )
    
    def _map_urgency_to_priority(self, urgency: Optional[str]) -> str:
        mapping = {"high": 1, "medium": 2, "low": 3}
        return mapping.get(urgency, 2)


# ============================================================================
# JOBBER CONNECTOR
# ============================================================================

class JobberAdapter(APIBasedCRMAdapter):
    """
    Jobber integration.
    Uses: OAuth 2.0 + GraphQL API
    Two-way sync capable for customers and jobs.
    """
    
    BASE_URL = "https://api.getjobber.com/graphql"
    
    def get_name(self) -> str:
        return "Jobber"
    
    def validate_credentials(self) -> Tuple[bool, str]:
        """Verify OAuth token is valid."""
        if not self.config_data.get("access_token"):
            return False, "OAuth access token not configured"
        return True, "OAuth token configured"
    
    def get_required_fields(self) -> List[str]:
        return ["caller_name", "caller_phone", "service_type"]
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Jobber uses Bearer token."""
        token = self.config_data.get("access_token")
        return {"Authorization": f"Bearer {token}"} if token else {}
    
    async def send_intake(self, intake: StandardizedIntake) -> HandoffResult:
        """
        Send intake to Jobber via GraphQL API.
        Jobber supports full two-way sync.
        """
        try:
            idempotency_key = intake.extra_fields.get("idempotency_key")
            # Create customer mutation
            customer_mutation = """
            mutation CreateCustomer($input: CreateCustomerInput!) {
                customerCreate(input: $input) {
                    customer { id email firstName lastName phoneNumber }
                    userErrors { message }
                }
            }
            """
            
            customer_vars = {
                "input": {
                    "firstName": intake.caller_name or "Unknown",
                    "phone": intake.caller_phone,
                    "email": intake.caller_email,
                    "clientMutationId": idempotency_key,
                }
            }

            success, response = await self._graphql_request(customer_mutation, customer_vars, idempotency_key=idempotency_key)
            
            if not success or response.get("errors"):
                logger.warning(f"Jobber customer creation failed")
                return await self._send_via_fallback(intake)
            
            customer_id = response.get("data", {}).get("customerCreate", {}).get("customer", {}).get("id")
            
            # Create job mutation
            job_mutation = """
            mutation CreateJob($input: CreateJobInput!) {
                jobCreate(input: $input) {
                    job { id title description address }
                    userErrors { message }
                }
            }
            """
            
            job_vars = {
                "input": {
                    "customerId": customer_id,
                    "title": intake.service_type or "Service Call",
                    "description": intake.service_description,
                    "clientMutationId": idempotency_key,
                }
            }

            success, response = await self._graphql_request(job_mutation, job_vars, idempotency_key=idempotency_key)
            
            if success and not response.get("errors"):
                job = response.get("data", {}).get("jobCreate", {}).get("job", {})
                return HandoffResult(
                    success=True,
                    method=HandoffMethod.API,
                    external_record_id=job.get("id"),
                    payload_sent={"customer": customer_vars, "job": job_vars},
                    response_received=job,
                )
            else:
                return await self._send_via_fallback(intake)
        
        except Exception as e:
            logger.error(f"Jobber handoff error: {str(e)}")
            return await self._send_via_fallback(intake)
    
    async def _graphql_request(self, query: str, variables: Dict[str, Any], idempotency_key: Optional[str] = None) -> Tuple[bool, Dict]:
        """Execute GraphQL request."""
        session = await self.get_http_session()
        headers = self.get_auth_headers()
        headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        
        try:
            response = await session.post(
                self.BASE_URL,
                headers=headers,
                json={"query": query, "variables": variables}
            )
            response.raise_for_status()
            return True, response.json()
        except Exception as e:
            return False, {"error": str(e)}
    
    async def _send_via_fallback(self, intake: StandardizedIntake) -> HandoffResult:
        """Fallback to webhook."""
        webhook_url = self.config_data.get("webhook_url")
        if not webhook_url:
            return HandoffResult(
                success=False,
                method=HandoffMethod.API,
                error_message="Jobber API failed and no webhook configured",
                retry_able=True,
            )
        
        payload = await self._create_fallback_payload(intake)
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
            return HandoffResult(
                success=True,
                method=HandoffMethod.WEBHOOK,
                payload_sent=payload,
                warnings=["Sent via webhook fallback"],
            )
        except Exception as e:
            return HandoffResult(
                success=False,
                method=HandoffMethod.WEBHOOK,
                error_message=str(e),
                retry_able=True,
            )


# ============================================================================
# GOOGLE CALENDAR CONNECTOR
# ============================================================================

class GoogleCalendarAdapter(APIBasedCRMAdapter):
    """
    Google Calendar integration.
    Uses: OAuth 2.0
    Creates calendar events for appointments.
    """
    
    BASE_URL = "https://www.googleapis.com/calendar/v3"
    
    def get_name(self) -> str:
        return "Google Calendar"
    
    def validate_credentials(self) -> Tuple[bool, str]:
        """Verify OAuth token is valid."""
        if not self.config_data.get("access_token"):
            return False, "OAuth access token not configured"
        return True, "OAuth token configured"
    
    def get_required_fields(self) -> List[str]:
        return ["service_type", "preferred_time"]
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Google Calendar uses Bearer token."""
        token = self.config_data.get("access_token")
        return {"Authorization": f"Bearer {token}"} if token else {}
    
    async def send_intake(self, intake: StandardizedIntake) -> HandoffResult:
        """
        Create calendar event for appointment.
        """
        try:
            calendar_id = self.config_data.get("calendar_id", "primary")
            
            event_data = {
                "summary": f"{intake.service_type or 'Appointment'} - {intake.caller_name or 'No Name'}",
                "description": intake.service_description or "",
                "start": {
                    "dateTime": intake.preferred_time.isoformat() if intake.preferred_time else None,
                },
                "end": {
                    "dateTime": (intake.preferred_time.replace(hour=intake.preferred_time.hour + 1).isoformat() 
                                if intake.preferred_time else None),
                },
                "attendees": [
                    {"email": intake.caller_email}
                ] if intake.caller_email else [],
            }
            
            # Remove null values
            event_data = {k: v for k, v in event_data.items() if v}
            
            success, response = await self.api_request(
                "POST",
                f"{self.BASE_URL}/calendars/{calendar_id}/events",
                json=event_data
            )
            
            if success:
                return HandoffResult(
                    success=True,
                    method=HandoffMethod.API,
                    external_record_id=response.get("id"),
                    external_record_url=response.get("htmlLink"),
                    payload_sent=event_data,
                    response_received=response,
                )
            else:
                return HandoffResult(
                    success=False,
                    method=HandoffMethod.API,
                    error_message=str(response),
                    retry_able=True,
                )
        
        except Exception as e:
            logger.error(f"Google Calendar handoff error: {str(e)}")
            return HandoffResult(
                success=False,
                method=HandoffMethod.API,
                error_message=str(e),
                retry_able=True,
            )


# ============================================================================
# GOOGLE BUSINESS PROFILE CONNECTOR
# ============================================================================

class GoogleBusinessProfileAdapter(APIBasedCRMAdapter):
    """
    Google Business Profile integration.
    Uses: OAuth 2.0
    Creates posts and manages business profile updates.
    """
    
    BASE_URL = "https://mybusiness.googleapis.com/v4"
    
    def get_name(self) -> str:
        return "Google Business Profile"
    
    def validate_credentials(self) -> Tuple[bool, str]:
        """Verify OAuth token and location ID are configured."""
        if not self.config_data.get("access_token"):
            return False, "OAuth access token not configured"
        if not self.config_data.get("location_id"):
            return False, "Business location ID not configured"
        return True, "OAuth and location configured"
    
    def get_required_fields(self) -> List[str]:
        return ["service_type"]
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Google Business Profile uses Bearer token."""
        token = self.config_data.get("access_token")
        return {"Authorization": f"Bearer {token}"} if token else {}
    
    async def send_intake(self, intake: StandardizedIntake) -> HandoffResult:
        """
        Create post on Google Business Profile.
        Good for announcing new service offerings or promotions.
        """
        try:
            location_id = self.config_data.get("location_id")
            
            post_data = {
                "summary": f"New {intake.service_type} inquiry received",
                "description": intake.service_description or intake.service_type,
            }
            
            success, response = await self.api_request(
                "POST",
                f"{self.BASE_URL}/accounts/*/locations/{location_id}/posts",
                json=post_data
            )
            
            if success:
                return HandoffResult(
                    success=True,
                    method=HandoffMethod.API,
                    external_record_id=response.get("name"),
                    payload_sent=post_data,
                    response_received=response,
                    warnings=["Post created but may require manual review"],
                )
            else:
                return HandoffResult(
                    success=False,
                    method=HandoffMethod.API,
                    error_message=str(response),
                    retry_able=False,  # API errors usually not retriable
                )
        
        except Exception as e:
            logger.error(f"Google Business Profile handoff error: {str(e)}")
            return HandoffResult(
                success=False,
                method=HandoffMethod.API,
                error_message=str(e),
                retry_able=False,
            )


# ============================================================================
# ZAPIER FALLBACK CONNECTOR
# ============================================================================

class ZapierAdapter(WebhookBasedCRMAdapter):
    """
    Zapier webhook fallback.
    Universal connector to any system via Zapier.
    """
    
    def get_name(self) -> str:
        return "Zapier"
    
    def validate_credentials(self) -> Tuple[bool, str]:
        """Verify webhook URL is configured."""
        if not self.config_data.get("webhook_url"):
            return False, "Zapier webhook URL not configured"
        return True, "Webhook URL configured"
    
    def get_required_fields(self) -> List[str]:
        return []  # Zapier is flexible
    
    async def send_intake(self, intake: StandardizedIntake) -> HandoffResult:
        """Send to Zapier webhook."""
        return await self.send_to_webhook(intake)
