"""
CDS Sync API — serves JoyVet CDS (offline HTML tool) case records.

Auth: clinic_key passed as ?key= query param (no Authorization header).
This avoids CORS credentialed-request restrictions when the HTML tool
is opened via file:// protocol.

CORS_ALLOW_ALL_ORIGINS = True covers the null origin from file://.
"""
import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import CdsCase

CLINIC_KEY_HEADER = 'key'


def _get_key(request):
    return request.GET.get(CLINIC_KEY_HEADER, '').strip()


def _bad_key():
    return JsonResponse({'error': 'Invalid or missing clinic key'}, status=401)


@method_decorator(csrf_exempt, name='dispatch')
class CdsCaseListView(View):
    """GET /api/v1/cds/cases/?key=<clinic_key>  — list all cases
       POST /api/v1/cds/cases/?key=<clinic_key> — upsert one case (body = JSON)
    """

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

        CdsCase.objects.update_or_create(
            clinic_key=key,
            case_id=case_id,
            defaults={'data': body},
        )
        return JsonResponse({'status': 'ok', 'case_id': case_id})


@method_decorator(csrf_exempt, name='dispatch')
class CdsCaseDetailView(View):
    """DELETE /api/v1/cds/cases/<case_id>/?key=<clinic_key>"""

    def delete(self, request, case_id):
        key = _get_key(request)
        if not key:
            return _bad_key()
        CdsCase.objects.filter(clinic_key=key, case_id=case_id).delete()
        return JsonResponse({'status': 'deleted'})
