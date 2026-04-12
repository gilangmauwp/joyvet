"""
Analytics API views — revenue reports, inventory forecast, dashboard stats.
"""
from datetime import date, timedelta

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import CanViewFinancials
from .reports import revenue_report, dashboard_stats


class RevenueReportView(APIView):
    permission_classes = [IsAuthenticated, CanViewFinancials]

    def get(self, request):
        branch_id = request.query_params.get('branch')
        if not branch_id:
            try:
                branch_id = request.user.staff_profile.branch_id
            except Exception:
                return Response({'error': 'branch parameter required'}, status=400)

        date_from_str = request.query_params.get('date_from', str(date.today() - timedelta(days=30)))
        date_to_str = request.query_params.get('date_to', str(date.today()))

        try:
            date_from = date.fromisoformat(date_from_str)
            date_to = date.fromisoformat(date_to_str)
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

        report = revenue_report(int(branch_id), date_from, date_to)
        return Response(report)


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            branch_id = request.user.staff_profile.branch_id
        except Exception:
            branch_id = request.query_params.get('branch')

        if not branch_id:
            return Response({'error': 'branch required'}, status=400)

        stats = dashboard_stats(int(branch_id))
        return Response(stats)


class InventoryForecastView(APIView):
    """Returns HTMX-renderable forecast table fragment."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.inventory.models import InventoryItem
        from django.db.models import F

        try:
            branch_id = request.user.staff_profile.branch_id
        except Exception:
            branch_id = request.query_params.get('branch')

        items = InventoryItem.objects.filter(
            branch_id=branch_id,
            is_active=True,
            category__in=['MED', 'VACCINE', 'SUPPLY'],
            avg_daily_consumption__isnull=False,
        ).order_by('predicted_stockout_date')

        data = []
        for item in items:
            days = None
            if item.predicted_stockout_date:
                from datetime import date
                days = (item.predicted_stockout_date - date.today()).days

            data.append({
                'id': item.pk,
                'name': item.name,
                'sku': item.sku,
                'stock_quantity': str(item.stock_quantity),
                'unit': item.unit,
                'avg_daily_consumption': str(item.avg_daily_consumption),
                'days_remaining': days,
                'predicted_stockout': (
                    item.predicted_stockout_date.isoformat()
                    if item.predicted_stockout_date else None
                ),
                'restock_recommendation': item.restock_recommendation,
                'urgency': (
                    'critical' if days is not None and days <= 7
                    else 'warning' if days is not None and days <= 30
                    else 'ok'
                ),
            })

        return Response(data)
