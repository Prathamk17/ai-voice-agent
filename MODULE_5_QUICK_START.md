# Module 5: Quick Start Guide

## Installation

1. **Install new dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   New packages for Module 5:
   - `jinja2` - Template engine (for future enhancements)
   - `openpyxl` - Excel file generation
   - `xlsxwriter` - Excel file writing
   - `prometheus-client` - Metrics collection

## Start the Application

```bash
python -m src.main
```

The application will start on `http://localhost:8000`

## Access the Dashboard

Open your browser and navigate to:

```
http://localhost:8000/static/dashboard.html
```

You'll see:
- System status indicator
- Key metrics (campaigns, leads, calls, success rates)
- Active calls in real-time
- Recent campaigns table
- Auto-refresh every 5 seconds

## API Endpoints

### 1. System Metrics

```bash
curl http://localhost:8000/analytics/system | jq
```

Returns overall system health and statistics.

### 2. Campaign Metrics

```bash
# Replace {campaign_id} with your campaign ID
curl http://localhost:8000/analytics/campaigns/1/metrics | jq
```

Returns detailed metrics for a specific campaign.

### 3. Dashboard Overview

```bash
curl http://localhost:8000/dashboard/overview | jq
```

Returns complete dashboard data.

### 4. Real-time Data

```bash
curl http://localhost:8000/dashboard/realtime | jq
```

Returns current call status and active calls.

### 5. Export Campaign Results

```bash
# Export as CSV
curl "http://localhost:8000/exports/campaigns/1/results?format=csv" -o campaign_results.csv

# Export as Excel
curl "http://localhost:8000/exports/campaigns/1/results?format=xlsx" -o campaign_results.xlsx
```

### 6. Export Call Transcripts

```bash
# Export transcripts as CSV
curl "http://localhost:8000/exports/campaigns/1/transcripts?format=csv" -o transcripts.csv

# Export as Excel
curl "http://localhost:8000/exports/campaigns/1/transcripts?format=xlsx" -o transcripts.xlsx
```

### 7. Health Checks

```bash
# Basic health
curl http://localhost:8000/health/

# Detailed health with component status
curl http://localhost:8000/health/detailed | jq

# Prometheus metrics
curl http://localhost:8000/health/metrics
```

## Testing

### Run Tests

```bash
# Run all Module 5 tests
pytest tests/test_analytics.py -v

# Run with output
pytest tests/test_analytics.py -v -s

# Run specific test
pytest tests/test_analytics.py::TestAnalyticsAPI::test_get_system_metrics_endpoint -v
```

## Common Use Cases

### 1. Monitor Campaign Performance

```python
import httpx
import asyncio

async def monitor_campaign(campaign_id: int):
    async with httpx.AsyncClient() as client:
        # Get campaign metrics
        response = await client.get(
            f"http://localhost:8000/analytics/campaigns/{campaign_id}/metrics"
        )
        metrics = response.json()

        print(f"Campaign: {metrics['campaign_name']}")
        print(f"Status: {metrics['status']}")
        print(f"Calls Completed: {metrics['calls_completed']}")
        print(f"Qualified: {metrics['calls_qualified']}")
        print(f"Answer Rate: {metrics['answer_rate']}%")
        print(f"Qualification Rate: {metrics['qualification_rate']}%")

# Run it
asyncio.run(monitor_campaign(1))
```

### 2. Watch Active Calls in Real-time

```python
import httpx
import asyncio

async def watch_active_calls():
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get("http://localhost:8000/dashboard/realtime")
            data = response.json()

            print(f"\n=== Active Calls: {data['calls_in_progress']} ===")
            for call in data['active_calls']:
                print(f"{call['lead_name']:20} | Stage: {call['stage']:15} | {call['duration_seconds']}s")

            await asyncio.sleep(5)

# Run it (Ctrl+C to stop)
asyncio.run(watch_active_calls())
```

### 3. Daily Performance Report

```python
import httpx
import asyncio
from datetime import datetime

async def daily_report(campaign_id: int):
    async with httpx.AsyncClient() as client:
        # Get daily stats for last 7 days
        response = await client.get(
            f"http://localhost:8000/analytics/daily-stats?campaign_id={campaign_id}&days=7"
        )
        daily_stats = response.json()

        print(f"\n=== Daily Performance Report (Last 7 Days) ===\n")
        print(f"{'Date':<12} {'Calls':<8} {'Answered':<10} {'Qualified':<10} {'Avg Duration'}")
        print("-" * 60)

        for stat in daily_stats:
            print(
                f"{stat['date']:<12} "
                f"{stat['calls_made']:<8} "
                f"{stat['calls_answered']:<10} "
                f"{stat['calls_qualified']:<10} "
                f"{stat['avg_duration_seconds']:.1f}s"
            )

asyncio.run(daily_report(1))
```

### 4. Export All Campaign Data

```python
import httpx
import asyncio

async def export_all_data(campaign_id: int):
    async with httpx.AsyncClient() as client:
        # Export results
        response = await client.get(
            f"http://localhost:8000/exports/campaigns/{campaign_id}/results?format=xlsx"
        )
        with open(f"campaign_{campaign_id}_results.xlsx", "wb") as f:
            f.write(response.content)
        print(f"✓ Exported results to campaign_{campaign_id}_results.xlsx")

        # Export transcripts
        response = await client.get(
            f"http://localhost:8000/exports/campaigns/{campaign_id}/transcripts?format=xlsx"
        )
        with open(f"campaign_{campaign_id}_transcripts.xlsx", "wb") as f:
            f.write(response.content)
        print(f"✓ Exported transcripts to campaign_{campaign_id}_transcripts.xlsx")

        # Export leads
        response = await client.get(
            f"http://localhost:8000/exports/campaigns/{campaign_id}/leads?format=xlsx"
        )
        with open(f"campaign_{campaign_id}_leads.xlsx", "wb") as f:
            f.write(response.content)
        print(f"✓ Exported leads to campaign_{campaign_id}_leads.xlsx")

asyncio.run(export_all_data(1))
```

## Dashboard Features

### Real-time Updates

The dashboard automatically refreshes:
- **Active calls**: Every 5 seconds
- **Dashboard overview**: Every 30 seconds
- **Last update timestamp**: Displayed in the header

### Metrics Cards

- **Total Campaigns**: Shows total with active count
- **Total Leads**: Count across all campaigns
- **Calls Today**: Today's calls with in-progress count
- **Answer Rate**: Last 30 days success rate
- **Qualification Rate**: Percentage of answered calls that qualified

### Campaign Table

- Campaign name and current status
- Calls completed and qualified counts
- Success rate percentages
- Quick export buttons for CSV downloads

## Monitoring Setup (Optional)

### Prometheus

1. Install Prometheus

2. Add to `prometheus.yml`:
   ```yaml
   scrape_configs:
     - job_name: 'voice-ai'
       static_configs:
         - targets: ['localhost:8000']
       metrics_path: '/health/metrics'
   ```

3. Start Prometheus and view metrics at `http://localhost:9090`

### Grafana Dashboards

Import these queries:

```promql
# Active Calls
active_calls

# Call Success Rate (5min)
rate(calls_completed_total{outcome="qualified"}[5m]) / rate(calls_completed_total[5m])

# Average Call Duration
rate(call_duration_seconds_sum[5m]) / rate(call_duration_seconds_count[5m])

# LLM Response Time (95th percentile)
histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m]))

# Error Rate
rate(errors_total[5m])
```

## Troubleshooting

### Dashboard Shows "Loading..."

1. Check the backend is running:
   ```bash
   curl http://localhost:8000/health/
   ```

2. Check browser console for errors (F12)

3. Verify static files are served:
   ```bash
   curl http://localhost:8000/static/dashboard.html
   ```

### No Metrics Data

1. Ensure you have campaigns with call data:
   ```bash
   curl http://localhost:8000/campaigns/
   ```

2. Check if calls have been made

3. Verify database connection:
   ```bash
   curl http://localhost:8000/health/detailed
   ```

### Export Returns Empty File

1. Verify campaign exists:
   ```bash
   curl http://localhost:8000/analytics/campaigns/{id}/metrics
   ```

2. Check if campaign has leads

3. Review server logs for errors

### Metrics Endpoint Not Working

1. Check prometheus-client is installed:
   ```bash
   pip list | grep prometheus
   ```

2. Verify metrics are being recorded in service logs

## API Documentation

View complete API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Next Steps

1. ✅ Install dependencies
2. ✅ Start the application
3. ✅ Open the dashboard
4. ✅ Test API endpoints
5. ✅ Run tests
6. 📊 Monitor your campaigns!

## Support

For detailed information, see:
- [MODULE_5_README.md](MODULE_5_README.md) - Full documentation
- [API Documentation](http://localhost:8000/docs) - Interactive API docs
- [tests/test_analytics.py](tests/test_analytics.py) - Usage examples

## Summary

Module 5 provides:

✅ Real-time dashboard UI
✅ Campaign analytics API
✅ Data export (CSV & Excel)
✅ System health monitoring
✅ Prometheus metrics
✅ Comprehensive testing

Your Voice AI Agent now has complete monitoring and analytics! 🎉
