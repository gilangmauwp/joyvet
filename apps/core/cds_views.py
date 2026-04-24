"""
CDS Sync API — serves JoyVet CDS (offline HTML tool) case records.

Auth: clinic_key passed as ?key= query param (no Authorization header).
CORS_ALLOW_ALL_ORIGINS = True covers the null origin from file://.
"""
import json
from collections import defaultdict
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import CdsCase

CLINIC_KEY_HEADER = 'key'
VALID_KEYS = {'6d51fab9-2bd6-49c6-b2ab-1eba585e5cc3'}


def _get_key(request):
    return request.GET.get(CLINIC_KEY_HEADER, '').strip()


def _bad_key():
    return JsonResponse({'error': 'Invalid or missing clinic key'}, status=401)


# ── Case list / upsert ────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class CdsCaseListView(View):
    """GET /api/v1/cds/cases/?key=  — list all cases (JSON)
       POST /api/v1/cds/cases/?key= — upsert one case"""

    def get(self, request):
        key = _get_key(request)
        if not key:
            return _bad_key()
        cases = list(
            CdsCase.objects.filter(clinic_key=key)
            .order_by('-saved_at')
            .values_list('data', flat=True)
        )
        return JsonResponse({'cases': cases})

    def post(self, request):
        key = _get_key(request)
        if not key:
            return _bad_key()
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        case_id = body.get('id')
        if not case_id:
            return JsonResponse({'error': 'Missing case id'}, status=400)

        # Pull out HTML (may be large) and store separately
        html_content = body.pop('_html', '') or ''
        if not isinstance(html_content, str):
            html_content = ''

        CdsCase.objects.update_or_create(
            clinic_key=key,
            case_id=case_id,
            defaults={'data': body, 'html_content': html_content},
        )
        return JsonResponse({'status': 'ok', 'case_id': case_id})


# ── Case detail (delete) ──────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class CdsCaseDetailView(View):
    """DELETE /api/v1/cds/cases/<case_id>/?key="""

    def delete(self, request, case_id):
        key = _get_key(request)
        if not key:
            return _bad_key()
        CdsCase.objects.filter(clinic_key=key, case_id=case_id).delete()
        return JsonResponse({'status': 'deleted'})


# ── HTML record download ──────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class CdsCaseHtmlView(View):
    """GET /api/v1/cds/cases/<case_id>/html/?key=  — serve printable HTML"""

    def get(self, request, case_id):
        key = _get_key(request)
        if not key:
            return _bad_key()
        try:
            case = CdsCase.objects.get(clinic_key=key, case_id=case_id)
        except CdsCase.DoesNotExist:
            return HttpResponse('Record not found', status=404)

        if not case.html_content:
            return HttpResponse('HTML not available for this record', status=404)

        return HttpResponse(case.html_content, content_type='text/html; charset=utf-8')


# ── Records browser ───────────────────────────────────────────────────────────

class CdsRecordsBrowserView(View):
    """GET /records/?key=  — Human-readable records browser"""

    def get(self, request):
        key = _get_key(request)
        if not key:
            return HttpResponse(_records_login_page(), content_type='text/html')

        cases = CdsCase.objects.filter(clinic_key=key).order_by('-saved_at')
        return HttpResponse(
            _build_browser_html(cases, key),
            content_type='text/html; charset=utf-8',
        )


def _build_browser_html(cases, key):
    # Group: species → client → patient → [records]
    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for c in cases:
        d = c.data or {}
        species = (d.get('species') or 'Unknown').strip().title()
        client  = (d.get('ownerName') or d.get('owner') or 'Unknown Client').strip().title()
        patient = (d.get('patientName') or d.get('patient') or 'Unknown Patient').strip().title()
        tree[species][client][patient].append(c)

    rows = []
    for species in sorted(tree):
        rows.append(f'<details open class="sp-group"><summary class="sp-hd">🐾 {species}</summary>')
        for client in sorted(tree[species]):
            rows.append(f'<details open class="cl-group"><summary class="cl-hd">👤 {client}</summary>')
            for patient in sorted(tree[species][client]):
                rows.append(f'<details open class="pt-group"><summary class="pt-hd">🏥 {patient}</summary><ul class="rec-list">')
                for c in tree[species][client][patient]:
                    d = c.data or {}
                    date_str = (d.get('visitDate') or str(c.saved_at)[:10])
                    diag = (d.get('topDiagnosis') or
                            (d.get('resultsData') or {}).get('name') or '—')
                    doc  = d.get('doctorName') or ''
                    has_html = bool(c.html_content)
                    view_btn = (
                        f'<a href="/api/v1/cds/cases/{c.case_id}/html/?key={key}" '
                        f'target="_blank" class="btn-view">📄 View Record</a>'
                        if has_html else '<span class="no-html">No HTML yet</span>'
                    )
                    rows.append(
                        f'<li>'
                        f'<span class="rec-date">{date_str}</span>'
                        f'<span class="rec-diag">{diag}</span>'
                        f'{"<span class=rec-doc>" + doc + "</span>" if doc else ""}'
                        f'{view_btn}'
                        f'</li>'
                    )
                rows.append('</ul></details>')
            rows.append('</details>')
        rows.append('</details>')

    body = '\n'.join(rows) if rows else '<p class="empty">No records found.</p>'

    total = cases.count()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JoyVet Medical Records</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f4f8;color:#1a202c;padding:20px}}
  header{{background:#1a56db;color:#fff;padding:18px 24px;border-radius:12px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between}}
  header h1{{font-size:1.3rem;font-weight:700}}
  header span{{font-size:.85rem;opacity:.8}}
  details{{background:#fff;border-radius:10px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}}
  summary{{padding:14px 18px;cursor:pointer;font-weight:600;user-select:none;list-style:none;display:flex;align-items:center;gap:8px}}
  summary::-webkit-details-marker{{display:none}}
  summary::after{{content:'▾';margin-left:auto;font-size:.8rem;opacity:.5}}
  details[open]>summary::after{{content:'▴'}}
  .sp-hd{{background:#ebf4ff;color:#1a56db;font-size:1rem}}
  .cl-hd{{background:#f0fdf4;color:#166534;font-size:.95rem;padding-left:32px}}
  .pt-hd{{background:#fefce8;color:#854d0e;font-size:.9rem;padding-left:48px}}
  .sp-group{{margin-bottom:12px}}
  .cl-group,.pt-group{{margin:4px 8px 4px 16px;border-radius:8px}}
  .rec-list{{list-style:none;padding:0 16px 12px 64px}}
  .rec-list li{{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #f1f5f9;flex-wrap:wrap}}
  .rec-list li:last-child{{border-bottom:none}}
  .rec-date{{font-size:.8rem;color:#64748b;min-width:90px}}
  .rec-diag{{flex:1;font-weight:500;color:#1e293b}}
  .rec-doc{{font-size:.8rem;color:#94a3b8}}
  .btn-view{{background:#1a56db;color:#fff;padding:5px 14px;border-radius:6px;text-decoration:none;font-size:.8rem;font-weight:600;white-space:nowrap}}
  .btn-view:hover{{background:#1e40af}}
  .no-html{{font-size:.75rem;color:#94a3b8;font-style:italic}}
  .empty{{text-align:center;padding:60px;color:#94a3b8}}
  .stats{{font-size:.85rem;color:#fff;opacity:.85}}
</style>
</head>
<body>
<header>
  <h1>🏥 JoyVet Medical Records</h1>
  <span class="stats">{total} record{"s" if total != 1 else ""}</span>
</header>
{body}
</body>
</html>"""


def _records_login_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JoyVet Records — Access</title>
<style>
  body{font-family:system-ui,sans-serif;background:#f0f4f8;display:flex;align-items:center;justify-content:center;min-height:100vh}
  .box{background:#fff;padding:40px;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,.1);max-width:420px;width:90%;text-align:center}
  h1{font-size:1.4rem;margin-bottom:8px;color:#1a202c}
  p{color:#64748b;margin-bottom:24px;font-size:.9rem}
  input{width:100%;padding:12px;border:2px solid #e2e8f0;border-radius:8px;font-size:1rem;margin-bottom:12px}
  button{width:100%;padding:12px;background:#1a56db;color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer}
  button:hover{background:#1e40af}
</style>
</head>
<body>
<div class="box">
  <h1>🏥 JoyVet Records</h1>
  <p>Enter your clinic key to access medical records.</p>
  <input id="k" type="password" placeholder="Clinic key">
  <button onclick="location.href='/records/?key='+document.getElementById('k').value">Access Records</button>
</div>
</body>
</html>"""
