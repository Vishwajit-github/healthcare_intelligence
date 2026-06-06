def merge_specialist_outputs(outputs: dict[str, str]) -> str:
    sections = []
    for name, output in outputs.items():
        if output:
            sections.append(f"## {name}\n{output}")
    return "\n\n".join(sections)
