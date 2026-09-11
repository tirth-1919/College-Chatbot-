from typing import List, Dict, Any, Optional

class ResponseBuilder:
    @classmethod
    def build_blocks(
        cls,
        text_content: str,
        images: Optional[List[Dict[str, Any]]] = None,
        table_data: Optional[Dict[str, Any]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        provenance: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        blocks = []

        # 1. Main Text Block
        if text_content:
            blocks.append({
                "type": "text",
                "content": text_content
            })

        # 2. Real AIT Image Blocks (P0)
        if images:
            for img in images:
                blocks.append({
                    "type": "image",
                    "url": img.get("image_url", ""),
                    "thumbnail_url": img.get("thumbnail_url", ""),
                    "alt": img.get("title", "AIT Official Image"),
                    "title": img.get("title", ""),
                    "category": img.get("category", ""),
                    "source_url": img.get("source_url", ""),
                    "verified": img.get("verified", True)
                })

        # 3. Table Block
        if table_data:
            blocks.append({
                "type": "table",
                "data": table_data
            })

        # 4. Citations Block
        if citations:
            blocks.append({
                "type": "citation",
                "items": citations
            })

        # 5. Provenance Block (Clean user-facing attribution, no raw internal debugging)
        if provenance:
            blocks.append({
                "type": "provenance",
                "authority": provenance.get("authority", "Official AIT Records"),
                "source_domain": provenance.get("source_domain", "aitindia.in"),
                "verified_at": provenance.get("verified_at", "")
            })

        # 6. Suggested Follow-up Actions
        if suggestions:
            blocks.append({
                "type": "suggested_action",
                "items": suggestions
            })

        return blocks

    @classmethod
    def format_final_payload(
        cls,
        conversation_id: str,
        message_id: str,
        text_content: str,
        blocks: List[Dict[str, Any]],
        grounding_status: str = "verified"
    ) -> Dict[str, Any]:
        return {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "message": text_content,
            "blocks": blocks,
            "grounding_status": grounding_status
        }

response_builder = ResponseBuilder()
