# Module 5: Dashboard, Analytics & Monitoring

## Overview

Module 5 completes the Voice AI Real Estate Agent by providing comprehensive analytics, monitoring, and a real-time dashboard for tracking campaign performance and system health.

## Features Implemented

### 1. Analytics Service (`src/services/analytics_service.py`)

Comprehensive analytics calculations including:

- **Campaign Metrics**: Detailed statistics for individual campaigns
  - Call outcomes (qualified, not interested, no answer, failed)
  - Success rates (answer rate, qualification rate, conversion rate)
  - Duration metrics (average call duration, total call time)
  - Lead statistics (total, valid, DNC filtered)

- **Daily Statistics**: Historical data for the last N days
  - Calls made, answered, qualified per day
  - Call duration trends
  - Performance tracking over time

- **Conversation Metrics**: Detailed analysis of individual calls
  - Number of exchanges
  - Conversation stages reached
  - Objections encountered
  - Qualification outcomes

- **System Metrics**: Overall system health and performance
  - Total campaigns and active campaigns
  - Overall answer and qualification rates
  - Current call status (in progress, queued)
  - System component health (database, Redis, APIs)

- **Lead Activity**: Recent actions and status for leads
  - Call attempts and outcomes
  - Next scheduled actions
  - Current status tracking

### 2. Export Service (`src/services/export_service.py`)

Data export functionality in multiple formats:

- **Campaign Results Export**
  - Lead information with contact details
  - Call outcomes and durations
  - Collected data (purpose, timeline, interest level)
  - Available in CSV and Excel formats

- **Call Transcripts Export**
  - Complete conversation transcripts
  - Call metadata (date, duration, outcome)
  - Lead information
  - Both CSV and Excel formats

- **Lead List Export**
  - Simple lead database export
  - Contact information
  - Property preferences
  - Call attempt history

### 3. API Endpoints

#### Analytics Endpoints (`src/api/analytics.py`)

```
GET /analytics/campaigns/{campaign_id}/metrics
- Get comprehensive metrics for a specific campaign

GET /analytics/daily-stats?campaign_id={id}&days={n}
- Get daily statistics for last N days
- Optional campaign filter

GET /analytics/conversations/{call_sid}
- Get detailed metrics for a single conversation

GET /analytics/system
- Get system-wide metrics and health status

GET /analytics/leads/activity?campaign_id={id}&limit={n}
- Get recent lead activity
- Filterable by campaign and status
```

#### Dashboard Endpoints (`src/api/dashboard.py`)

```
GET /dashboard/overview
- Complete dashboard overview
- System metrics, recent campaigns, daily stats

GET /dashboard/realtime
- Real-time updates for active calls
- Current call status
- Should be polled every 3-5 seconds

GET /dashboard/campaigns/{campaign_id}/summary
- Detailed summary for a specific campaign
- Includes metrics, daily stats, and recent activity
```

#### Export Endpoints (`src/api/exports.py`)

```
GET /exports/campaigns/{campaign_id}/results?format={csv|xlsx}
- Download campaign results

GET /exports/campaigns/{campaign_id}/transcripts?format={csv|xlsx}
- Download call transcripts

GET /exports/campaigns/{campaign_id}/leads?format={csv|xlsx}
- Download lead list
```

### 4. Prometheus Metrics (`src/monitoring/metrics.py`)

Real-time metrics collection for monitoring:

**Call Metrics:**
- `calls_initiated_total` - Counter of initiated calls
- `calls_completed_total` - Counter of completed calls
- `call_duration_seconds` - Histogram of call durations
- `active_calls` - Gauge of currently active calls
- `queued_calls` - Gauge of calls waiting in queue

**Campaign Metrics:**
- `campaign_status` - Gauge of campaign status (1=running, 0=not running)

**AI Service Metrics:**
- `llm_request_duration_seconds` - Histogram of LLM API latency
- `stt_request_duration_seconds` - Histogram of STT API latency
- `tts_request_duration_seconds` - Histogram of TTS API latency

**System Metrics:**
- `websocket_connections` - Gauge of active WebSocket connections
- `errors_total` - Counter of errors by type and component

**Metrics Endpoint:**
```
GET /health/metrics
- Prometheus-compatible metrics in text format
```

### 5. Health Checks (`src/monitoring/health_checks.py`)

Comprehensive system health monitoring:

- **Database Health**: Connection and query test
- **Redis Health**: Connection and read/write test
- **Exotel API Health**: API accessibility check
- **AI Services Health**: Deepgram, OpenAI, ElevenLabs status
- **Background Worker Health**: Scheduler running status

**Health Endpoints:**
```
GET /health/ - Basic health check
GET /health/ready - Readiness check (for load balancers)
GET /health/live - Liveness check (for orchestrators)
GET /health/detailed - Comprehensive health status
GET /health/metrics - Prometheus metrics
```

### 6. Dashboard UI (`static/dashboard.html`)

Real-time web dashboard with:

- **System Status**: Overall health indicator
- **Key Metrics Cards**:
  - Total campaigns (with active count)
  - Total leads
  - Calls today (with in-progress count)
  - Answer rate (last 30 days)
  - Qualification rate

- **Active Calls Section**:
  - Live updates every 5 seconds
  - Lead name, conversation stage, duration

- **Recent Campaigns Table**:
  - Campaign name and status
  - Calls completed and qualified
  - Answer and qualification rates
  - Quick export buttons

- **Auto-Refresh**:
  - Real-time data updates every 5 seconds
  - Dashboard overview refresh every 30 seconds
  - Last update timestamp

**Access Dashboard:**
```
http://localhost:8000/static/dashboard.html
```

## Updated Services with Metrics

The following services have been updated to record Prometheus metrics:

### LLM Service (`src/ai/llm_service.py`)
- Records request duration for GPT-4o-mini calls
- Tracks errors in LLM generation

### STT Service (`src/ai/stt_service.py`)
- Records transcription duration
- Tracks STT errors

### TTS Service (`src/ai/tts_service.py`)
- Records speech generation duration
- Tracks TTS errors

## Installation

### Dependencies

Add to `requirements.txt` (already added):

```
# Module 5: Dashboard, Analytics & Monitoring
jinja2>=3.1.3
openpyxl>=3.1.2
xlsxwriter>=3.1.9
prometheus-client>=0.19.0
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage Examples

### 1. Get Campaign Metrics

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("http://localhost:8000/analytics/campaigns/1/metrics")
    metrics = response.json()

    print(f"Answer Rate: {metrics['answer_rate']}%")
    print(f"Qualification Rate: {metrics['qualification_rate']}%")
    print(f"Qualified Leads: {metrics['calls_qualified']}")
```

### 2. Export Campaign Results

```python
import httpx

async with httpx.AsyncClient() as client:
    # Export as Excel
    response = await client.get(
        "http://localhost:8000/exports/campaigns/1/results?format=xlsx"
    )

    with open("campaign_results.xlsx", "wb") as f:
        f.write(response.content)
```

### 3. Monitor System Health

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("http://localhost:8000/health/detailed")
    health = response.json()

    print(f"Overall Status: {health['status']}")
    print(f"Database: {health['checks']['database']['status']}")
    print(f"Redis: {health['checks']['redis']['status']}")
```

### 4. Get Real-time Dashboard Data

```python
import httpx
import asyncio

async def monitor_calls():
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get("http://localhost:8000/dashboard/realtime")
            data = response.json()

            print(f"Calls in Progress: {data['calls_in_progress']}")
            for call in data['active_calls']:
                print(f"  - {call['lead_name']}: {call['stage']} ({call['duration_seconds']}s)")

            await asyncio.sleep(5)  # Update every 5 seconds
```

## Testing

### Run Analytics Tests

```bash
# Run all Module 5 tests
pytest tests/test_analytics.py -v

# Run specific test class
pytest tests/test_analytics.py::TestAnalyticsService -v

# Run with coverage
pytest tests/test_analytics.py --cov=src.services.analytics_service --cov=src.services.export_service
```

### Manual Testing Checklist

1. **Start the application**:
   ```bash
   python -m src.main
   ```

2. **Check system health**:
   ```bash
   curl http://localhost:8000/health/detailed
   ```

3. **View Prometheus metrics**:
   ```bash
   curl http://localhost:8000/health/metrics
   ```

4. **Open dashboard**:
   - Navigate to: `http://localhost:8000/static/dashboard.html`
   - Verify real-time updates are working
   - Check that metrics cards display correctly

5. **Test analytics endpoints**:
   ```bash
   # System metrics
   curl http://localhost:8000/analytics/system

   # Daily stats
   curl http://localhost:8000/analytics/daily-stats?days=7
   ```

6. **Test exports**:
   ```bash
   # Export campaign results as CSV
   curl http://localhost:8000/exports/campaigns/1/results?format=csv -o results.csv

   # Export as Excel
   curl http://localhost:8000/exports/campaigns/1/results?format=xlsx -o results.xlsx
   ```

## Monitoring with Prometheus

### Sample Prometheus Configuration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'voice-ai-agent'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/health/metrics'
    scrape_interval: 15s
```

### Sample Grafana Dashboard Queries

**Active Calls:**
```promql
active_calls
```

**Call Success Rate:**
```promql
rate(calls_completed_total{outcome="qualified"}[5m]) / rate(calls_completed_total[5m])
```

**Average Call Duration:**
```promql
rate(call_duration_seconds_sum[5m]) / rate(call_duration_seconds_count[5m])
```

**LLM Response Time (P95):**
```promql
histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m]))
```

**Error Rate:**
```promql
rate(errors_total[5m])
```

## Project Structure

```
voice-ai-real-estate/
├── src/
│   ├── api/
│   │   ├── analytics.py          # Analytics endpoints
│   │   ├── dashboard.py          # Dashboard endpoints
│   │   └── exports.py            # Export endpoints
│   ├── services/
│   │   ├── analytics_service.py  # Analytics calculations
│   │   └── export_service.py     # Data export service
│   ├── schemas/
│   │   └── analytics.py          # Analytics Pydantic models
│   └── monitoring/
│       ├── metrics.py             # Prometheus metrics
│       └── health_checks.py      # Health check system
├── static/
│   └── dashboard.html            # Web dashboard UI
├── tests/
│   └── test_analytics.py         # Analytics tests
└── MODULE_5_README.md            # This file
```

## API Documentation

Full API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Performance Considerations

1. **Dashboard Polling**: The dashboard polls `/dashboard/realtime` every 5 seconds. Adjust if needed for your server capacity.

2. **Metrics Collection**: Prometheus metrics have minimal overhead but can be disabled by removing the metrics import if not needed.

3. **Export Large Datasets**: For campaigns with thousands of leads, exports may take time. Consider implementing pagination or background jobs for very large exports.

4. **Database Queries**: Analytics queries use aggregation. Ensure proper indexes on:
   - `call_sessions.initiated_at`
   - `call_sessions.status`
   - `call_sessions.outcome`
   - `leads.campaign_id`
   - `scheduled_calls.status`

## Troubleshooting

### Dashboard Not Loading

- Check that static files are mounted correctly in `main.py`
- Verify the static directory exists
- Check browser console for errors

### Metrics Endpoint Returns Empty

- Ensure Prometheus client is installed
- Check that services are recording metrics
- Verify METRICS_ENABLED is True in service files

### Export Fails

- Check campaign exists in database
- Verify openpyxl is installed for Excel exports
- Check database connection

### Health Check Reports Unhealthy

- Check individual component status in detailed health endpoint
- Verify Redis is running
- Check database connectivity
- Ensure API keys are configured

## Next Steps

Module 5 completes the core functionality. Consider these enhancements:

1. **Advanced Analytics**:
   - Conversion funnel visualization
   - A/B testing support for different scripts
   - Lead quality scoring

2. **Real-time Notifications**:
   - WebSocket for instant dashboard updates
   - Email/SMS alerts for qualified leads
   - Slack integration for team notifications

3. **Enhanced Reporting**:
   - PDF report generation
   - Scheduled email reports
   - Custom date range queries

4. **Performance Optimization**:
   - Redis caching for analytics
   - Database query optimization
   - Background job processing for exports

## Summary

Module 5 provides complete visibility into your Voice AI Agent's performance with:

✅ Real-time dashboard
✅ Comprehensive analytics
✅ Data export (CSV/Excel)
✅ Prometheus metrics
✅ System health monitoring
✅ Campaign performance tracking
✅ API for custom integrations

The system is now production-ready with full monitoring and analytics capabilities!
