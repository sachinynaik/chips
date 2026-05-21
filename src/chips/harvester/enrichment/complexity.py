from __future__ import annotations

class LizardAnalyzer:
    def analyze(self, file_paths: list[str]) -> list[dict]:
        try:
            import lizard
        except ImportError:
            return []
        results = []
        for fp in file_paths:
            try:
                analysis = lizard.analyze_file(fp)
                for func in analysis.function_list:
                    results.append({
                        "file": fp,
                        "function": func.name,
                        "cyclomatic_complexity": func.cyclomatic_complexity,
                        "nloc": func.nloc,
                    })
            except Exception:
                pass
        return results
