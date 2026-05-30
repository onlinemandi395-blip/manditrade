from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class ProductCatalogService:
    def __init__(self, governance_service, id_allocator_service, notification_center_service=None, gmail_service=None, admin_email: str | None = None) -> None:
        self.governance_service = governance_service
        self.id_allocator_service = id_allocator_service
        self.notification_center_service = notification_center_service
        self.gmail_service = gmail_service
        self.admin_email = (admin_email or "").strip().lower()

    def list_products(
        self,
        *,
        include_pending: bool = True,
        viewer_role: str | None = None,
        viewer_code: str | None = None,
    ) -> list[dict[str, Any]]:
        products = self.governance_service.list_products()
        def present(item: dict[str, Any]) -> dict[str, Any]:
            return self._sanitize_for_viewer(item, viewer_role=viewer_role, viewer_code=viewer_code)
        active_visible_products = [
            present(item)
            for item in products
            if item.get("status") == "ACTIVE" and item.get("visible", True)
        ]
        if viewer_role == "platform_admin":
            return [dict(item) for item in products] if include_pending else active_visible_products
        if viewer_role in {"manufacturer", "admin_as_manufacturer"}:
            return [
                present(item)
                for item in products
                if (item.get("status") == "ACTIVE" and item.get("visible", True))
                or (
                    viewer_code
                    and (
                        item.get("created_by_manufacturer_id") == viewer_code
                        or item.get("created_by") == viewer_code
                    )
                )
            ]
        return active_visible_products

    def propose_product(
        self,
        *,
        created_by: str,
        name: str,
        category: str,
        unit: str,
        description: str = "",
        suggested_mandi_price: float = 0,
        suggested_mrp: float = 0,
        visibility_request: str = "MANDI_NETWORK",
        minimum_order_qty: int = 1,
        available_for_public_sale: bool = False,
        available_for_mandi_network: bool = True,
        image_url: str = "",
        created_by_email: str = "",
    ) -> dict[str, Any]:
        created_at = datetime.now(UTC).isoformat()
        product = {
            "product_id": self.id_allocator_service.allocate("product"),
            "name": name.strip(),
            "category": category.strip(),
            "unit": unit.strip(),
            "description": description.strip(),
            "suggested_mandi_price": float(suggested_mandi_price or 0),
            "suggested_mrp": float(suggested_mrp or 0),
            "approved_mandi_price": None,
            "approved_mrp": None,
            "visibility_request": visibility_request.strip().upper() or "MANDI_NETWORK",
            "approved_visibility": None,
            "minimum_order_qty": max(int(minimum_order_qty or 1), 1),
            "available_for_public_sale": bool(available_for_public_sale),
            "available_for_mandi_network": bool(available_for_mandi_network),
            "image_url": image_url.strip(),
            "mandi_price": 0,
            "mrp": 0,
            "status": "PROPOSED",
            "comments": [],
            "clarification_status": "NONE",
            "created_by": created_by,
            "created_by_manufacturer_id": created_by,
            "created_by_email": created_by_email.strip().lower(),
            "approved_by": "",
            "admin_note": "",
            "created_at": created_at,
            "updated_at": created_at,
            "approved_at": "",
            "visible": False,
        }
        self.governance_service.upsert_product(product)
        return product

    def approve_product(
        self,
        *,
        product_id: str,
        approved_by: str,
        approved_mandi_price: float | None = None,
        approved_mrp: float | None = None,
        mandi_price: float | None = None,
        mrp: float | None = None,
        category: str | None = None,
        unit: str | None = None,
        approved_visibility: str | None = None,
        visible: bool = True,
        admin_note: str = "",
    ) -> dict[str, Any]:
        products = self.governance_service.list_products()
        product = next((item for item in products if item.get("product_id") == product_id), None)
        if product is None:
            raise ValueError(f"Product not found: {product_id}")
        if product.get("clarification_status") == "ADMIN_QUERY":
            raise ValueError("Product cannot be approved while admin clarification is unresolved.")
        final_mandi_price = float(
            approved_mandi_price
            if approved_mandi_price is not None
            else mandi_price
            if mandi_price is not None
            else product.get("suggested_mandi_price", 0)
        )
        final_mrp = float(
            approved_mrp
            if approved_mrp is not None
            else mrp
            if mrp is not None
            else product.get("suggested_mrp", 0)
        )
        final_visibility = (approved_visibility or product.get("visibility_request") or "PUBLIC").strip().upper()
        product.update(
            {
                "mandi_price": final_mandi_price,
                "mrp": final_mrp,
                "approved_mandi_price": final_mandi_price,
                "approved_mrp": final_mrp,
                "status": "ACTIVE",
                "approved_by": approved_by,
                "approved_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "category": (category or product.get("category", "")).strip(),
                "unit": (unit or product.get("unit", "")).strip(),
                "approved_visibility": final_visibility,
                "visible": bool(visible),
                "admin_note": admin_note.strip(),
                "clarification_status": product.get("clarification_status") or "NONE",
            }
        )
        self.governance_service.upsert_product(product)
        return product

    def reject_product(self, *, product_id: str, approved_by: str, admin_note: str = "") -> dict[str, Any]:
        products = self.governance_service.list_products()
        product = next((item for item in products if item.get("product_id") == product_id), None)
        if product is None:
            raise ValueError(f"Product not found: {product_id}")
        product.update(
            {
                "status": "REJECTED",
                "approved_by": approved_by,
                "approved_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "visible": False,
                "admin_note": admin_note.strip(),
            }
        )
        self.governance_service.upsert_product(product)
        return product

    def update_product(
        self,
        *,
        product_id: str,
        updates: dict[str, Any],
        updated_by: str,
    ) -> dict[str, Any]:
        product = self._get_product(product_id)
        allowed_fields = {
            "name",
            "category",
            "unit",
            "description",
            "suggested_mandi_price",
            "suggested_mrp",
            "approved_mandi_price",
            "approved_mrp",
            "visibility_request",
            "approved_visibility",
            "minimum_order_qty",
            "available_for_public_sale",
            "available_for_mandi_network",
            "image_url",
            "visible",
            "admin_note",
            "status",
        }
        for key, value in updates.items():
            if key not in allowed_fields:
                continue
            product[key] = value
        if "approved_mandi_price" in updates and updates.get("approved_mandi_price") is not None:
            product["mandi_price"] = float(updates["approved_mandi_price"])
        if "approved_mrp" in updates and updates.get("approved_mrp") is not None:
            product["mrp"] = float(updates["approved_mrp"])
        if "minimum_order_qty" in updates:
            product["minimum_order_qty"] = max(int(updates.get("minimum_order_qty") or 1), 1)
        if "name" in updates:
            product["name"] = str(updates["name"]).strip()
        if "category" in updates:
            product["category"] = str(updates["category"]).strip()
        if "unit" in updates:
            product["unit"] = str(updates["unit"]).strip()
        if "description" in updates:
            product["description"] = str(updates["description"]).strip()
        if "visibility_request" in updates:
            product["visibility_request"] = str(updates["visibility_request"]).strip().upper()
        if "approved_visibility" in updates:
            product["approved_visibility"] = str(updates["approved_visibility"]).strip().upper()
        if "image_url" in updates:
            product["image_url"] = str(updates["image_url"]).strip()
        if "admin_note" in updates:
            product["admin_note"] = str(updates["admin_note"]).strip()
        product["updated_at"] = datetime.now(UTC).isoformat()
        product["approved_by"] = updated_by or product.get("approved_by", "")
        self.governance_service.upsert_product(product)
        return product

    def delete_product(self, *, product_id: str) -> bool:
        return self.governance_service.delete_product(product_id)

    def add_product_comment(self, product_id: str, author_user, message: str) -> dict[str, Any]:
        product = self._get_product(product_id)
        self._ensure_comment_access(product, author_user)
        normalized_message = message.strip()
        if not normalized_message:
            raise ValueError("Comment message is required.")
        author_role = self._normalized_role(author_user.role)
        author_user_id = self._author_user_id(author_user)
        comment = {
            "comment_id": self.id_allocator_service.allocate("comment"),
            "author_user_id": author_user_id,
            "author_role": author_role,
            "author_email": author_user.email.strip().lower(),
            "message": normalized_message,
            "created_at": datetime.now(UTC).isoformat(),
            "visibility": "INVOLVED_PARTIES",
            "read_by": [author_user_id],
        }
        comments = list(product.get("comments", []) or [])
        comments.append(comment)
        product["comments"] = comments
        next_status = "ADMIN_QUERY" if author_role == "PLATFORM_ADMIN" else "MANUFACTURER_REPLIED"
        product["clarification_status"] = next_status
        product["updated_at"] = datetime.now(UTC).isoformat()
        self.governance_service.upsert_product(product)
        self._notify_comment_event(product, author_user, comment)
        return comment

    def list_product_comments(self, product_id: str, viewer_user) -> list[dict[str, Any]]:
        product = self._get_product(product_id)
        self._ensure_comment_access(product, viewer_user)
        viewer_user_id = self._author_user_id(viewer_user)
        comments = [dict(item) for item in product.get("comments", []) or []]
        changed = False
        for item in comments:
            read_by = list(item.get("read_by", []) or [])
            if viewer_user_id not in read_by:
                read_by.append(viewer_user_id)
                item["read_by"] = read_by
                changed = True
        if changed:
            product["comments"] = comments
            product["updated_at"] = datetime.now(UTC).isoformat()
            self.governance_service.upsert_product(product)
        return comments

    def mark_clarification_resolved(self, product_id: str, admin_user) -> dict[str, Any]:
        product = self._get_product(product_id)
        if self._normalized_role(admin_user.role) != "PLATFORM_ADMIN":
            raise PermissionError("Only platform admin can mark clarification resolved.")
        product["clarification_status"] = "RESOLVED"
        product["updated_at"] = datetime.now(UTC).isoformat()
        self.governance_service.upsert_product(product)
        return product

    def set_clarification_status(self, product_id: str, status: str) -> dict[str, Any]:
        if status not in {"NONE", "ADMIN_QUERY", "MANUFACTURER_REPLIED", "RESOLVED"}:
            raise ValueError(f"Unsupported clarification status: {status}")
        product = self._get_product(product_id)
        product["clarification_status"] = status
        product["updated_at"] = datetime.now(UTC).isoformat()
        self.governance_service.upsert_product(product)
        return product

    def get_product(self, product_id: str) -> dict[str, Any]:
        return self._get_product(product_id)

    def _get_product(self, product_id: str) -> dict[str, Any]:
        products = self.governance_service.list_products()
        product = next((item for item in products if item.get("product_id") == product_id), None)
        if product is None:
            raise ValueError(f"Product not found: {product_id}")
        product.setdefault("comments", [])
        product.setdefault("clarification_status", "NONE")
        return product

    def _normalized_role(self, role: str) -> str:
        mapping = {
            "platform_admin": "PLATFORM_ADMIN",
            "admin": "PLATFORM_ADMIN",
            "manufacturer": "MANUFACTURER",
            "admin_as_manufacturer": "ADMIN_AS_MANUFACTURER",
        }
        normalized = mapping.get((role or "").strip().lower())
        if not normalized:
            raise PermissionError("User cannot comment on product proposals.")
        return normalized

    def _author_user_id(self, user) -> str:
        if self._normalized_role(user.role) == "PLATFORM_ADMIN":
            return (getattr(user, "email", "") or "PLATFORM_ADMIN").strip().lower() or "PLATFORM_ADMIN"
        return (getattr(user, "manufacturer_code", "") or getattr(user, "email", "")).strip()

    def _ensure_comment_access(self, product: dict[str, Any], user) -> None:
        role = self._normalized_role(user.role)
        if role == "PLATFORM_ADMIN":
            return
        creator_code = product.get("created_by_manufacturer_id") or product.get("created_by") or ""
        if getattr(user, "manufacturer_code", "") != creator_code:
            raise PermissionError("Only the proposing manufacturer can access proposal comments.")

    def _notify_comment_event(self, product: dict[str, Any], author_user, comment: dict[str, Any]) -> None:
        if not self.notification_center_service:
            return
        author_role = comment["author_role"]
        manufacturer_code = product.get("created_by_manufacturer_id") or product.get("created_by") or ""
        product_name = product.get("name", product.get("product_id", "product"))
        if author_role == "PLATFORM_ADMIN":
            creator_email = (product.get("created_by_email") or "").strip().lower()
            if manufacturer_code:
                self.notification_center_service.create_notification(
                    manufacturer_code,
                    user_id=manufacturer_code,
                    notification_type="PRODUCT_PROPOSAL_COMMENTED",
                    priority="HIGH",
                    title="Product proposal needs clarification",
                    message=f"Platform admin commented on {product_name}.",
                    source_type="PRODUCT_PROPOSAL",
                    source_id=product["product_id"],
                )
            if self.gmail_service and creator_email:
                self.gmail_service.enqueue_message(
                    creator_email,
                    f"Clarification needed for {product_name}",
                    f"Platform admin commented on your product proposal: {comment['message']}",
                    "product_proposal_commented",
                )
            return

        if manufacturer_code:
            self.notification_center_service.create_notification(
                manufacturer_code,
                user_id=self.admin_email or "PLATFORM_ADMIN",
                notification_type="PRODUCT_PROPOSAL_REPLIED",
                priority="HIGH",
                title="Manufacturer replied to product proposal",
                message=f"Manufacturer replied on {product_name}.",
                source_type="PRODUCT_PROPOSAL",
                source_id=product["product_id"],
            )
        if self.gmail_service and self.admin_email:
            self.gmail_service.enqueue_message(
                self.admin_email,
                f"Manufacturer replied on {product_name}",
                f"The manufacturer replied on product proposal {product_name}: {comment['message']}",
                "product_proposal_replied",
            )

    def _sanitize_for_viewer(self, product: dict[str, Any], *, viewer_role: str | None, viewer_code: str | None) -> dict[str, Any]:
        result = dict(product)
        creator_code = product.get("created_by_manufacturer_id") or product.get("created_by") or ""
        can_view_comments = viewer_role == "platform_admin" or (
            viewer_role in {"manufacturer", "admin_as_manufacturer"} and viewer_code == creator_code
        )
        if not can_view_comments:
            result.pop("comments", None)
            result.pop("clarification_status", None)
            result.pop("admin_note", None)
        return result
