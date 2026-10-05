from __future__ import annotations
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from dehalu.domain.models import AnalyzerCoverage, StaticFinding
from dehalu.verification.adapters import get_adapter, normalize

RULES = Path(__file__).parent / 'rules'


def analyze(code: str, language: str) -> tuple[dict[str, list[StaticFinding]], list[AnalyzerCoverage]]:
    language = normalize(language)
    adapter = get_adapter(language)
    parsed, coverage = adapter.parse(code) if adapter else ([], AnalyzerCoverage(analyzer='parser', language=language, status='unavailable', detail='No installed grammar adapter'))
    sast, scan_coverage = scan(code, language)
    return {'tree_sitter': parsed, 'semgrep': sast}, [coverage, scan_coverage, *([adapter.coverage()[1]] if adapter else [])]


def scan(code: str, language: str) -> tuple[list[StaticFinding], AnalyzerCoverage]:
    binary = shutil.which('semgrep') or str(Path(os.sys.executable).parent / 'semgrep')
    if not Path(binary).is_file():
        return [], AnalyzerCoverage(analyzer='semgrep', language=language, status='unavailable', detail='Semgrep not installed')
    suffix = {'python': '.py', 'javascript': '.jsx', 'typescript': '.tsx', 'java': '.java', 'go': '.go', 'rust': '.rs', 'c': '.c', 'cpp': '.cpp'}.get(language)
    if not suffix:
        return [], AnalyzerCoverage(analyzer='semgrep', language=language, status='unavailable', detail='No rules for target language')
    with tempfile.TemporaryDirectory(prefix='dehalu-') as directory:
        path = Path(directory) / ('snippet' + suffix)
        path.write_text(code)
        try:
            # Explicit target/config, no registry, autofix, execution, dependency builds, or telemetry.
            env = {**os.environ, 'SEMGREP_SEND_METRICS': 'off', 'SEMGREP_ENABLE_VERSION_CHECK': '0', 'XDG_CONFIG_HOME': directory}
            result = subprocess.run([binary, 'scan', '--config', str(RULES), '--no-rewrite-rule-ids', '--json', '--metrics=off', '--disable-version-check', '--disable-nosem', '--no-git-ignore', '--quiet', str(path)], cwd=directory, env=env, capture_output=True, text=True, timeout=45)
            payload = json.loads(result.stdout)
            findings = []
            for item in payload.get('results', []):
                extra = item.get('extra', {})
                start, end = item['start'], item['end']
                findings.append(StaticFinding(rule_id=item['check_id'], severity={'ERROR': 'error', 'WARNING': 'warning', 'INFO': 'info'}.get(extra.get('severity'), 'warning'), message=extra.get('message', 'Static rule match'), location=f"line {start['line']}", source_range={'start_line': start['line'], 'start_column': start['col'], 'end_line': end['line'], 'end_column': end['col']}, evidence_source='Semgrep 1.136.0 / local rules 2.0'))
            errors = payload.get('errors', [])
            status = 'failed' if result.returncode not in {0, 1} else 'partial' if errors else 'available'
            return findings, AnalyzerCoverage(analyzer='semgrep', language=language, status=status, detail='Local rules completed' if not errors else str(errors)[:500], version='1.136.0/rules-2.0')
        except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
            return [], AnalyzerCoverage(analyzer='semgrep', language=language, status='failed', detail=f'Scan failed: {type(exc).__name__}')


def run_static_analysis_by_stage(code: str, language: str) -> dict[str, list[StaticFinding]]:
    return analyze(code, language)[0]


def run_static_analysis(code: str, language: str) -> list[StaticFinding]:
    staged = run_static_analysis_by_stage(code, language)
    return staged['tree_sitter'] + staged['semgrep']
