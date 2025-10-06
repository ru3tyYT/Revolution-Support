# modules/prompts.py
def build_troubleshoot_prompt(title: str, messages_text: str, log_excerpt: str = None, few_shot_examples=None) -> str:
    """
    Build a compact, information-dense prompt for troubleshooting.
    few_shot_examples: list of fixes (dicts) to append as examples.
    """
    parts = [f"Thread title: {title}", "Messages:", messages_text]
    if log_excerpt:
        parts.extend(["Attached logs (excerpt):", log_excerpt])
    if few_shot_examples:
        parts.append("\nPrevious fixes for reference:")
        for ex in few_shot_examples:
            parts.append(f"- {ex.get('problem_summary','')}: {ex.get('fix','')[:120]}...")
    user_block = "\n".join(parts)
    return (
        "System: You are an expert support technician. Output JSON with keys: summary, confidence (0-1), fixes (array of steps), files_to_change (optional). Keep summary <60 words.\n"
        f"User: {user_block}\n"
        "Task: Identify root cause, list steps to fix, provide commands or code snippets if applicable. Return only JSON."
    )

def build_enhance_prompt(problem: str, solution: str) -> str:
    return (
        "System: You are an editor that improves problem descriptions and solutions for a public knowledge base. Output improved problem and improved solution.\n"
        f"Problem: {problem}\nSolution: {solution}"
    )

def build_summary_prompt(thread_text: str) -> str:
    return (
        "System: Summarize the thread into problem, steps, fix_snippet and a confidence 0-1. Keep concise.\n"
        f"Thread: {thread_text}"
    )
