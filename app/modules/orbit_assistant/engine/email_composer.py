"""
Email Composer — Generates professional emails via LLM based on user intent.
"""
from typing import Dict
from openai import AsyncOpenAI
import json

from .logger import get_logger

log = get_logger("email_composer")

class EmailComposer:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def compose(self, raw_intent: str, recipient: str, sender_name: str) -> Dict[str, str]:
        system_prompt = f"""You are a professional workplace email writer for a governance system.
Write a formal, polite, and concise email based on the user's raw message.

Sender name: {sender_name}
Recipient: {recipient}

Requirements:
- Subject line must be concise and contextually appropriate.
- Start the body with "Dear [Recipient Name]," or "Hello,".
- Write in a professional but empathetic workplace tone.
- Keep the body concise (2-4 sentences max).
- End with "Best regards," followed by "{sender_name}" on a new line.

Return ONLY valid JSON with keys:
- "subject": "A concise, professional subject line"
- "body": "The complete, formatted email body text"
"""
        
        try:
            from app.core.config import settings
            resolved_model = settings.GROK_MODEL
            response = await self.client.chat.completions.create(
                model=resolved_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Intent: {raw_intent}"}
                ],
                temperature=0.3,
            )
            
            raw = response.choices[0].message.content.strip()
            
            # Robust JSON extraction
            start_idx = raw.find("{")
            end_idx = raw.rfind("}")
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                cleaned = raw[start_idx:end_idx + 1]
            else:
                cleaned = raw
                
            # Use strict=False to allow raw control characters like tabs/newlines in strings
            # which LLMs frequently output even when told not to.
            parsed = json.loads(cleaned, strict=False)
            
            return {
                "subject": parsed.get("subject", "Message from Orbit System"),
                "body": parsed.get("body", "No content provided.")
            }
        except Exception as e:
            log.error(f"Failed to compose email: {e}")
            # Fallback
            return {
                "subject": "System Notification",
                "body": f"Automated message regarding: {raw_intent}\n\nBest regards,\n{sender_name}"
            }
