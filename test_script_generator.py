"""
Quick manual test for the script generator -- run this once Ollama is
installed and the model is pulled, before we build the image/voice/video
modules. This alone proves the first stage of the pipeline works.

Setup (one time):
    1. Install Ollama from https://ollama.com
    2. In one terminal:   ollama serve
    3. In another:        ollama pull llama3.2:3b

Then run:
    python test_script_generator.py
"""

from modules.script_generator import ScriptRequest, generate_script
from modules.project_manager import Project

if __name__ == "__main__":
    request = ScriptRequest(
        idea="A shy kid who's scared of the dark discovers a firefly that guides them home",
        story_type="emotional",
        visual_style="children's book watercolor illustration",
        duration_seconds=45,
        character_description=(
            "An 8-year-old girl with curly red hair, a yellow raincoat, "
            "freckles, and big curious eyes"
        ),
    )

    print("Generating script (this can take a while on a CPU-only machine)...")
    result = generate_script(request)

    if result.warnings:
        print("\nGenerated, but with warnings:")
        for w in result.warnings:
            print(f"  - {w}")
    else:
        print("\nClean generation, no validation issues.")

    project = Project(result.raw["title"])
    project.save_script(result.raw)

    print(f"\nTitle: {result.raw['title']}")
    print(f"Scenes: {len(result.raw['scenes'])}")
    print(f"Saved to: {project.root.resolve()}")
