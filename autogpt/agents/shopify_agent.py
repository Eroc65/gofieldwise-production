"""Shopify Agent — e-commerce product, order, and revenue operations.

Responsibilities
----------------
* List products and check inventory levels.
* Retrieve orders and calculate revenue totals.
* Fetch customer records and order history.
* Create discount codes for promotions.
* GPT-compose e-commerce performance reports.

Configuration
-------------
``SHOPIFY_STORE_DOMAIN`` — Your Shopify store domain, e.g.
    ``"my-store.myshopify.com"`` (no ``https://``).
``SHOPIFY_ACCESS_TOKEN`` — Admin API access token from the Shopify
    partner dashboard or custom-app setup.  The token needs
    ``read_products``, ``read_orders``, ``read_customers``, and
    ``write_price_rules`` scopes.

No third-party SDK is required; the agent uses the Shopify Admin REST API
(version 2024-01) via plain ``requests``.
"""

from __future__ import annotations

import logging
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_SHOPIFY_API_VERSION = "2024-01"

_ECOMMERCE_REPORT_PROMPT = """\
You are an e-commerce analyst preparing a concise performance summary.
Given a JSON object with Shopify store metrics, write a 3-5 sentence
plain-text summary covering: recent order volume and revenue, top-selling
products if available, any low-stock alerts, and one actionable
recommendation to increase sales.
Output ONLY the summary — no preamble, no markdown, no JSON.
"""


class ShopifyAgent:
    """E-commerce product, order, and revenue operations via the Shopify Admin REST API.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
    """

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        openai.api_key = config.openai_api_key

    # ------------------------------------------------------------------ #
    # Products
    # ------------------------------------------------------------------ #

    def list_products(self, limit: int = 20, status: str = "active") -> list[dict[str, Any]]:
        """List products in the store.

        Args:
            limit: Number of products to return (1–250).
            status: Product status filter — ``"active"``, ``"draft"``,
                ``"archived"``, or ``"any"``.

        Returns:
            List of product summary dicts.
        """
        self._require_credentials()
        data = self._get(
            "/products.json",
            params={"limit": max(1, min(limit, 250)), "status": status},
        )
        products = data.get("products", [])
        return [
            {
                "id": p.get("id"),
                "title": p.get("title", ""),
                "status": p.get("status", ""),
                "vendor": p.get("vendor", ""),
                "product_type": p.get("product_type", ""),
                "variants_count": len(p.get("variants", [])),
                "inventory_quantity": sum(
                    v.get("inventory_quantity", 0) or 0 for v in p.get("variants", [])
                ),
            }
            for p in products
        ]

    def get_product(self, product_id: str) -> dict[str, Any]:
        """Retrieve full details for a single product.

        Args:
            product_id: Shopify product ID.

        Returns:
            Product dict with variants, inventory, and pricing.
        """
        self._require_credentials()
        data = self._get(f"/products/{product_id}.json")
        p = data.get("product", {})
        return {
            "id": p.get("id"),
            "title": p.get("title", ""),
            "status": p.get("status", ""),
            "vendor": p.get("vendor", ""),
            "variants": [
                {
                    "id": v.get("id"),
                    "title": v.get("title", ""),
                    "price": v.get("price", ""),
                    "inventory_quantity": v.get("inventory_quantity", 0),
                    "sku": v.get("sku", ""),
                }
                for v in p.get("variants", [])
            ],
        }

    def get_low_inventory(self, threshold: int = 5) -> list[dict[str, Any]]:
        """Return products/variants with inventory at or below a threshold.

        Args:
            threshold: Inventory quantity considered low (default 5).

        Returns:
            List of dicts with ``product_id``, ``title``, ``variant_title``,
            and ``inventory_quantity``.
        """
        self._require_credentials()
        products = self.list_products(limit=250)
        low: list[dict[str, Any]] = []
        for product in products:
            if product["inventory_quantity"] <= threshold:
                low.append(
                    {
                        "product_id": product["id"],
                        "title": product["title"],
                        "inventory_quantity": product["inventory_quantity"],
                    }
                )
        return low

    # ------------------------------------------------------------------ #
    # Orders
    # ------------------------------------------------------------------ #

    def list_orders(
        self,
        status: str = "open",
        limit: int = 20,
        financial_status: str = "paid",
    ) -> list[dict[str, Any]]:
        """List store orders.

        Args:
            status: Fulfillment status — ``"open"``, ``"closed"``,
                ``"cancelled"``, or ``"any"``.
            limit: Number of orders to return (1–250).
            financial_status: ``"paid"``, ``"pending"``, ``"refunded"``,
                ``"any"``, etc.

        Returns:
            List of order summary dicts.
        """
        self._require_credentials()
        data = self._get(
            "/orders.json",
            params={
                "status": status,
                "limit": max(1, min(limit, 250)),
                "financial_status": financial_status,
            },
        )
        orders = data.get("orders", [])
        return [
            {
                "id": o.get("id"),
                "name": o.get("name", ""),
                "email": o.get("email", ""),
                "total_price": o.get("total_price", "0.00"),
                "currency": o.get("currency", ""),
                "financial_status": o.get("financial_status", ""),
                "fulfillment_status": o.get("fulfillment_status", ""),
                "created_at": o.get("created_at", ""),
                "line_items_count": len(o.get("line_items", [])),
            }
            for o in orders
        ]

    def get_revenue_summary(self, limit: int = 50) -> dict[str, Any]:
        """Compute revenue totals from recent paid orders.

        Args:
            limit: Number of recent paid orders to analyse.

        Returns:
            Dict with ``total_revenue``, ``order_count``, ``average_order_value``,
            and ``currency``.
        """
        self._require_credentials()
        orders = self.list_orders(status="any", limit=limit, financial_status="paid")
        if not orders:
            return {
                "total_revenue": 0.0,
                "order_count": 0,
                "average_order_value": 0.0,
                "currency": self._cfg.shopify_currency,
            }
        total = sum(float(o.get("total_price", 0)) for o in orders)
        currency = orders[0].get("currency", self._cfg.shopify_currency)
        return {
            "total_revenue": round(total, 2),
            "order_count": len(orders),
            "average_order_value": round(total / len(orders), 2),
            "currency": currency,
        }

    # ------------------------------------------------------------------ #
    # Customers
    # ------------------------------------------------------------------ #

    def list_customers(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent customers.

        Args:
            limit: Number of customers to return (1–250).

        Returns:
            List of customer summary dicts.
        """
        self._require_credentials()
        data = self._get("/customers.json", params={"limit": max(1, min(limit, 250))})
        customers = data.get("customers", [])
        return [
            {
                "id": c.get("id"),
                "email": c.get("email", ""),
                "first_name": c.get("first_name", ""),
                "last_name": c.get("last_name", ""),
                "orders_count": c.get("orders_count", 0),
                "total_spent": c.get("total_spent", "0.00"),
            }
            for c in customers
        ]

    # ------------------------------------------------------------------ #
    # Discounts
    # ------------------------------------------------------------------ #

    def create_discount_code(
        self,
        code: str,
        percent_off: float = 10.0,
        usage_limit: int = 100,
    ) -> dict[str, Any]:
        """Create a percentage-based discount code.

        Creates a price rule and attaches the given discount code to it.

        Args:
            code: Discount code string (e.g. ``"LAUNCH20"``).
            percent_off: Percentage discount value (e.g. ``20`` for 20% off).
            usage_limit: Maximum number of times the code may be used.

        Returns:
            Dict with ``code``, ``price_rule_id``, and ``discount_code_id``.
        """
        self._require_credentials()
        # Create the price rule
        rule_resp = requests.post(
            self._url("/price_rules.json"),
            headers=self._headers(),
            json={
                "price_rule": {
                    "title": code,
                    "target_type": "line_item",
                    "target_selection": "all",
                    "allocation_method": "across",
                    "value_type": "percentage",
                    "value": f"-{abs(percent_off)}",
                    "customer_selection": "all",
                    "usage_limit": usage_limit,
                    "starts_at": "2000-01-01T00:00:00Z",
                }
            },
            timeout=20,
        )
        rule_resp.raise_for_status()
        price_rule = rule_resp.json().get("price_rule", {})
        price_rule_id = price_rule.get("id")

        # Attach the discount code
        code_resp = requests.post(
            self._url(f"/price_rules/{price_rule_id}/discount_codes.json"),
            headers=self._headers(),
            json={"discount_code": {"code": code}},
            timeout=20,
        )
        code_resp.raise_for_status()
        discount_code = code_resp.json().get("discount_code", {})
        self._log.info("Created discount code %s (rule %s)", code, price_rule_id)
        return {
            "code": code,
            "price_rule_id": price_rule_id,
            "discount_code_id": discount_code.get("id"),
        }

    # ------------------------------------------------------------------ #
    # Reports
    # ------------------------------------------------------------------ #

    def generate_store_report(self) -> dict[str, Any]:
        """Generate a GPT-written e-commerce performance report.

        Returns:
            Dict with ``report`` (plain text) and ``metrics`` (raw data).
        """
        import json

        revenue = self.get_revenue_summary()
        low_stock = self.get_low_inventory()
        recent_products = self.list_products(limit=10)
        metrics = {
            "revenue": revenue,
            "low_stock_count": len(low_stock),
            "low_stock_items": low_stock[:5],
            "total_active_products": len(recent_products),
        }
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _ECOMMERCE_REPORT_PROMPT},
                {"role": "user", "content": json.dumps(metrics, default=str)},
            ],
            temperature=0.4,
            max_tokens=300,
        )
        report = (response.choices[0].message.content or "No data available.").strip()
        return {"report": report, "metrics": metrics}

    # ------------------------------------------------------------------ #
    # Orchestrator entry point
    # ------------------------------------------------------------------ #

    def run(self, task: str) -> dict[str, Any]:
        """Orchestrator entry point.

        Recognises keywords:
        * ``"list products"`` / ``"show products"`` / ``"inventory"`` → :meth:`list_products`
        * ``"low stock"`` / ``"low inventory"`` → :meth:`get_low_inventory`
        * ``"list orders"`` / ``"show orders"`` / ``"recent orders"`` → :meth:`list_orders`
        * ``"revenue"`` / ``"sales"`` / ``"income"`` → :meth:`get_revenue_summary`
        * ``"customers"`` / ``"buyers"`` → :meth:`list_customers`
        * ``"discount"`` / ``"promo code"`` / ``"coupon"`` → :meth:`create_discount_code`
        * ``"report"`` / ``"summary"`` / (default) → :meth:`generate_store_report`

        Args:
            task: Natural-language task description.

        Returns:
            Result dict.
        """
        t = task.lower()

        if any(kw in t for kw in ("low stock", "low inventory", "out of stock", "restock")):
            items = self.get_low_inventory()
            return {"low_stock_items": items, "count": len(items)}

        if any(kw in t for kw in ("list products", "show products", "all products", "inventory")):
            products = self.list_products()
            return {"products": products, "count": len(products)}

        if any(kw in t for kw in ("list orders", "show orders", "recent orders", "open orders")):
            orders = self.list_orders()
            return {"orders": orders, "count": len(orders)}

        if any(kw in t for kw in ("revenue", "sales total", "income", "earnings")):
            return self.get_revenue_summary()

        if any(kw in t for kw in ("list customers", "show customers", "buyers")):
            customers = self.list_customers()
            return {"customers": customers, "count": len(customers)}

        if any(kw in t for kw in ("discount", "promo code", "coupon", "voucher")):
            # Try to extract an uppercase code from the task
            code = ""
            for token in task.split():
                clean = token.strip(".,;\"'")
                if clean.isupper() and len(clean) >= 3:
                    code = clean
                    break
            if not code:
                code = "PROMO10"
            return self.create_discount_code(code=code)

        # Default: full store report
        return self.generate_store_report()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_credentials(self) -> None:
        if not self._cfg.shopify_store_domain or not self._cfg.shopify_access_token:
            raise ValueError(
                "SHOPIFY_STORE_DOMAIN and SHOPIFY_ACCESS_TOKEN must both be configured."
            )

    def _base_url(self) -> str:
        return (
            f"https://{self._cfg.shopify_store_domain}"
            f"/admin/api/{_SHOPIFY_API_VERSION}"
        )

    def _url(self, path: str) -> str:
        return f"{self._base_url()}{path}"

    def _headers(self) -> dict[str, str]:
        return {
            "X-Shopify-Access-Token": self._cfg.shopify_access_token,
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = requests.get(
            self._url(path),
            headers=self._headers(),
            params=params or {},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()
