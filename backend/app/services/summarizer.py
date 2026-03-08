"""Local LLM story arc summarizer using Ollama.

Takes structured scene/character logs and generates
narrative summaries of story arcs.
"""

import httpx
from loguru import logger

from app.core.config import settings


SYSTEM_PROMPT = """You are an anime episode analyst. Given a structured log of scenes, 
characters, and their interactions, produce a clear narrative summary.

Format your response as:
- **Arc Title**: A compelling title for this story arc
- **Summary**: A 2-4 paragraph narrative summary
- **Key Characters**: List the main characters involved
- **Key Events**: Bullet points of important plot points

Be specific about character actions and motivations. Use present tense."""


class Summarizer:
    """Generates story arc summaries from scene/character logs using a local LLM."""

    def __init__(self):
        self._base_url = settings.ollama_host
        self._model = settings.ollama_model

    async def generate_summary(
        self,
        scene_logs: list[dict],
        character_info: list[dict],
        detail_level: str = "medium",
    ) -> dict:
        """
        Generate a story arc summary from scene and character data.

        Args:
            scene_logs: List of scene data with timestamps, descriptions, characters
            character_info: List of character data with names, appearances
            detail_level: "brief", "medium", or "detailed"

        Returns:
            {title: str, summary: str, characters: list, events: list}
        """
        # Build context from structured data
        context = self._build_context(scene_logs, character_info)

        detail_instruction = {
            "brief": "Provide a 1-paragraph summary.",
            "medium": "Provide a 2-3 paragraph summary with key events.",
            "detailed": "Provide a comprehensive 4-5 paragraph summary with detailed analysis.",
        }.get(detail_level, "Provide a 2-3 paragraph summary with key events.")

        prompt = f"""Analyze the following anime scene log and produce a story arc summary.

{detail_instruction}

=== SCENE LOG ===
{context}
=== END LOG ===

Produce a structured narrative summary."""

        try:
            response = await self._chat(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return {
                "title": "Summary Unavailable",
                "summary": f"Failed to generate summary: {str(e)}",
                "characters": [],
                "events": [],
            }

    async def describe_character(self, character_data: dict) -> str:
        """Generate a natural language description of a character."""
        prompt = f"""Based on the following observation data, write a brief character description 
for an anime character wiki entry (2-3 sentences).

Character observations:
- First seen: {character_data.get('first_seen', 'unknown')}
- Appearance count: {character_data.get('appearance_count', 0)}
- Scenes: {character_data.get('scenes', [])}
- Co-appearing characters: {character_data.get('co_appearing', [])}
- Detected items nearby: {character_data.get('nearby_items', [])}

Write a wiki-style character description."""

        try:
            return await self._chat(prompt)
        except Exception as e:
            logger.error(f"Character description failed: {e}")
            return "Description unavailable."

    async def _chat(self, prompt: str) -> str:
        """Send a prompt to Ollama and get the response."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    def _build_context(self, scene_logs: list[dict], character_info: list[dict]) -> str:
        """Format scene and character data into a readable context string."""
        lines = []

        # Characters section
        if character_info:
            lines.append("CHARACTERS:")
            for char in character_info:
                lines.append(
                    f"  - {char.get('name', 'Unknown')} "
                    f"(seen {char.get('appearance_count', 0)} times)"
                )
            lines.append("")

        # Scenes section
        lines.append("SCENES (chronological):")
        for scene in scene_logs:
            timestamp = scene.get("start_time", 0)
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            time_str = f"[{minutes:02d}:{seconds:02d}]"

            chars_in_scene = ", ".join(
                c.get("name", "Unknown") for c in scene.get("characters", [])
            )
            items = ", ".join(
                item.get("label", "") for item in scene.get("items", [])
            )

            location = scene.get("location", "Unknown location")
            desc = scene.get("description", "")

            lines.append(f"  {time_str} Scene #{scene.get('scene_index', '?')}:")
            lines.append(f"    Location: {location}")
            if chars_in_scene:
                lines.append(f"    Characters: {chars_in_scene}")
            if items:
                lines.append(f"    Items: {items}")
            if desc:
                lines.append(f"    Description: {desc}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _parse_response(text: str) -> dict:
        """Parse the LLM response into structured data."""
        result = {
            "title": "",
            "summary": "",
            "characters": [],
            "events": [],
        }

        sections = text.split("**")
        current_section = ""

        for part in sections:
            part_lower = part.strip().lower()
            if "arc title" in part_lower or "title" in part_lower:
                current_section = "title"
            elif "summary" in part_lower:
                current_section = "summary"
            elif "key characters" in part_lower or "characters" in part_lower:
                current_section = "characters"
            elif "key events" in part_lower or "events" in part_lower:
                current_section = "events"
            elif current_section == "title":
                result["title"] = part.strip().strip(":").strip()
            elif current_section == "summary":
                result["summary"] += part.strip() + " "
            elif current_section in ("characters", "events"):
                items = [
                    line.strip().lstrip("-•").strip()
                    for line in part.strip().split("\n")
                    if line.strip() and line.strip() not in (":", "")
                ]
                result[current_section].extend(items)

        result["summary"] = result["summary"].strip()

        if not result["title"]:
            result["title"] = "Untitled Arc"

        return result


# Singleton
_summarizer: Summarizer | None = None


def get_summarizer() -> Summarizer:
    global _summarizer
    if _summarizer is None:
        _summarizer = Summarizer()
    return _summarizer
