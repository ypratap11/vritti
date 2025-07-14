# scripts/monitor.py - Comprehensive monitoring and alerting system
"""
Advanced monitoring system for Vritti Invoice AI
Monitors health, performance, errors, and sends alerts
"""

import asyncio
import aiohttp
import psutil
import time
import json
import logging
import smtplib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import sqlite3
from pathlib import Path


# Configuration
@dataclass
class MonitorConfig:
    api_url: str = "http://localhost:8000"
    check_interval: int = 300  # 5 minutes
    alert_threshold: int = 3  # Failures before alert

    # Thresholds
    cpu_threshold: float = 80.0
    memory_threshold: float = 85.0
    disk_threshold: float = 90.0
    response_time_threshold: float = 10.0

    # Notification settings
    slack_webhook: Optional[str] = None
    email_smtp_server: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_recipients: List[str] = None

    # Database
    db_path: str = "monitoring.db"
    log_file: str = "monitoring.log"

    def __post_init__(self):
        # Load from environment variables
        self.api_url = os.getenv("MONITOR_API_URL", self.api_url)
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.email_username = os.getenv("EMAIL_USERNAME")
        self.email_password = os.getenv("EMAIL_PASSWORD")

        if os.getenv("EMAIL_RECIPIENTS"):
            self.email_recipients = os.getenv("EMAIL_RECIPIENTS").split(",")


@dataclass
class HealthCheck:
    timestamp: datetime
    service: str
    status: str
    response_time: float
    details: Dict[str, Any]
    error_message: Optional[str] = None


class MonitoringDatabase:
    """SQLite database for storing monitoring data"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                service TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time REAL,
                details TEXT,
                error_message TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                network_io TEXT,
                process_count INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE
            )
        ''')

        conn.commit()
        conn.close()

    def save_health_check(self, health_check: HealthCheck):
        """Save health check result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO health_checks 
            (timestamp, service, status, response_time, details, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            health_check.timestamp.isoformat(),
            health_check.service,
            health_check.status,
            health_check.response_time,
            json.dumps(health_check.details),
            health_check.error_message
        ))

        conn.commit()
        conn.close()

    def save_system_metrics(self, metrics: Dict[str, Any]):
        """Save system metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO system_metrics 
            (timestamp, cpu_percent, memory_percent, disk_percent, network_io, process_count)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            metrics.get('cpu_percent'),
            metrics.get('memory_percent'),
            metrics.get('disk_percent'),
            json.dumps(metrics.get('network_io', {})),
            metrics.get('process_count')
        ))

        conn.commit()
        conn.close()

    def save_alert(self, alert_type: str, severity: str, message: str):
        """Save alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO alerts (timestamp, alert_type, severity, message)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now().isoformat(), alert_type, severity, message))

        conn.commit()
        conn.close()

    def get_recent_failures(self, service: str, minutes: int = 15) -> int:
        """Get count of recent failures for a service"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        since = (datetime.now() - timedelta(minutes=minutes)).isoformat()

        cursor.execute('''
            SELECT COUNT(*) FROM health_checks 
            WHERE service = ? AND status = 'FAIL' AND timestamp > ?
        ''', (service, since))

        count = cursor.fetchone()[0]
        conn.close()
        return count


class AlertManager:
    """Handles sending alerts via various channels"""

    def __init__(self, config: MonitorConfig):
        self.config = config
        self.logger = logging.getLogger("AlertManager")

    async def send_alert(self, alert_type: str, severity: str, message: str):
        """Send alert via all configured channels"""
        full_message = f"🚨 Vritti AI Alert [{severity}]\n{alert_type}: {message}"

        # Send to Slack
        if self.config.slack_webhook:
            await self.send_slack_alert(full_message)

        # Send email
        if self.config.email_recipients:
            await self.send_email_alert(alert_type, full_message)

        # Log the alert
        self.logger.warning(f"Alert sent: {alert_type} - {message}")

    async def send_slack_alert(self, message: str):
        """Send alert to Slack"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"text": message}
                async with session.post(self.config.slack_webhook, json=payload) as response:
                    if response.status == 200:
                        self.logger.info("Slack alert sent successfully")
                    else:
                        self.logger.error(f"Failed to send Slack alert: {response.status}")
        except Exception as e:
            self.logger.error(f"Error sending Slack alert: {e}")

    async def send_email_alert(self, subject: str, message: str):
        """Send email alert"""
        try:
            msg = MimeMultipart()
            msg['From'] = self.config.email_username
            msg['To'] = ", ".join(self.config.email_recipients)
            msg['Subject'] = f"Vritti AI Alert: {subject}"

            msg.attach(MimeText(message, 'plain'))

            server = smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port)
            server.starttls()
            server.login(self.config.email_username, self.config.email_password)

            text = msg.as_string()
            server.sendmail(self.config.email_username, self.config.email_recipients, text)
            server.quit()

            self.logger.info("Email alert sent successfully")
        except Exception as e:
            self.logger.error(f"Error sending email alert: {e}")


class VrittiMonitor:
    """Main monitoring class"""

    def __init__(self, config: MonitorConfig):
        self.config = config
        self.db = MonitoringDatabase(config.db_path)
        self.alert_manager = AlertManager(config)
        self.failure_counts = {}

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(config.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("VrittiMonitor")

    async def check_api_health(self) -> HealthCheck:
        """Check API health endpoint"""
        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config.api_url}/", timeout=30) as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        data = await response.json()
                        status = "PASS" if data.get("status") == "healthy" else "FAIL"
                        details = {
                            "status_code": response.status,
                            "response_data": data,
                            "features": data.get("features", {})
                        }
                    else:
                        status = "FAIL"
                        details = {"status_code": response.status}

                    return HealthCheck(
                        timestamp=datetime.now(),
                        service="api_health",
                        status=status,
                        response_time=response_time,
                        details=details
                    )

        except Exception as e:
            return HealthCheck(
                timestamp=datetime.now(),
                service="api_health",
                status="FAIL",
                response_time=time.time() - start_time,
                details={},
                error_message=str(e)
            )

    async def check_invoice_processing(self) -> HealthCheck:
        """Test invoice processing endpoint"""
        start_time = time.time()

        try:
            # Create a simple test image
            from PIL import Image
            import io

            img = Image.new('RGB', (100, 100), color='white')
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()

            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', img_data, filename='test.png', content_type='image/png')

                async with session.post(f"{self.config.api_url}/api/v1/mobile/process-invoice",
                                        data=data, timeout=60) as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        result = await response.json()
                        status = "PASS"
                        details = {
                            "status_code": response.status,
                            "processing_time": result.get("processing_time"),
                            "mobile_optimized": result.get("mobile_optimized")
                        }
                    else:
                        status = "FAIL"
                        details = {"status_code": response.status}

                    return HealthCheck(
                        timestamp=datetime.now(),
                        service="invoice_processing",
                        status=status,
                        response_time=response_time,
                        details=details
                    )

        except Exception as e:
            return HealthCheck(
                timestamp=datetime.now(),
                service="invoice_processing",
                status="FAIL",
                response_time=time.time() - start_time,
                details={},
                error_message=str(e)
            )

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100

            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }

            # Process count
            process_count = len(psutil.pids())

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "network_io": network_io,
                "process_count": process_count,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error getting system metrics: {e}")
            return {}

    async def check_thresholds(self, metrics: Dict[str, Any]):
        """Check if metrics exceed thresholds and send alerts"""
        alerts = []

        # CPU threshold
        if metrics.get('cpu_percent', 0) > self.config.cpu_threshold:
            alerts.append(("SYSTEM", "HIGH",
                           f"CPU usage high: {metrics['cpu_percent']:.1f}%"))

        # Memory threshold
        if metrics.get('memory_percent', 0) > self.config.memory_threshold:
            alerts.append(("SYSTEM", "HIGH",
                           f"Memory usage high: {metrics['memory_percent']:.1f}%"))

        # Disk threshold
        if metrics.get('disk_percent', 0) > self.config.disk_threshold:
            alerts.append(("SYSTEM", "CRITICAL",
                           f"Disk usage critical: {metrics['disk_percent']:.1f}%"))

        # Send alerts
        for alert_type, severity, message in alerts:
            await self.alert_manager.send_alert(alert_type, severity, message)
            self.db.save_alert(alert_type, severity, message)

    async def check_service_health(self, health_check: HealthCheck):
        """Check service health and send alerts if needed"""
        if health_check.status == "FAIL":
            service = health_check.service
            self.failure_counts[service] = self.failure_counts.get(service, 0) + 1

            # Check if we've reached the alert threshold
            if self.failure_counts[service] >= self.config.alert_threshold:
                await self.alert_manager.send_alert(
                    "SERVICE", "CRITICAL",
                    f"{service} has failed {self.failure_counts[service]} times. "
                    f"Last error: {health_check.error_message or 'Unknown error'}"
                )
                self.db.save_alert("SERVICE", "CRITICAL",
                                   f"{service} failed {self.failure_counts[service]} times")

                # Reset counter after alerting
                self.failure_counts[service] = 0
        else:
            # Reset failure count on success
            self.failure_counts[health_check.service] = 0

    async def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        self.logger.info("Starting monitoring cycle...")

        # Check API health
        api_health = await self.check_api_health()
        self.db.save_health_check(api_health)
        await self.check_service_health(api_health)

        # Check invoice processing (only if API is healthy)
        if api_health.status == "PASS":
            processing_health = await self.check_invoice_processing()
            self.db.save_health_check(processing_health)
            await self.check_service_health(processing_health)

        # Get system metrics
        metrics = self.get_system_metrics()
        if metrics:
            self.db.save_system_metrics(metrics)
            await self.check_thresholds(metrics)

        self.logger.info("Monitoring cycle completed")

    async def run_continuous_monitoring(self):
        """Run continuous monitoring"""
        self.logger.info("Starting continuous monitoring...")

        while True:
            try:
                await self.run_monitoring_cycle()
                await asyncio.sleep(self.config.check_interval)
            except KeyboardInterrupt:
                self.logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring cycle: {e}")
                await asyncio.sleep(30)  # Short delay before retry

    def generate_status_report(self) -> Dict[str, Any]:
        """Generate a status report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get recent health checks
        cursor.execute('''
            SELECT service, status, COUNT(*) as count
            FROM health_checks 
            WHERE timestamp > datetime('now', '-1 hour')
            GROUP BY service, status
        ''')
        recent_health = cursor.fetchall()

        # Get recent alerts
        cursor.execute('''
            SELECT alert_type, severity, COUNT(*) as count
            FROM alerts 
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY alert_type, severity
        ''')
        recent_alerts = cursor.fetchall()

        # Get latest system metrics
        cursor.execute('''
            SELECT * FROM system_metrics 
            ORDER BY timestamp DESC LIMIT 1
        ''')
        latest_metrics = cursor.fetchone()

        conn.close()

        return {
            "timestamp": datetime.now().isoformat(),
            "recent_health_checks": recent_health,
            "recent_alerts": recent_alerts,
            "latest_system_metrics": latest_metrics,
            "uptime_status": "Operational" if not recent_alerts else "Issues Detected"
        }


# CLI for the monitoring system
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Vritti Invoice AI Monitoring System")
    parser.add_argument("--config", help="Config file path")
    parser.add_argument("--once", action="store_true", help="Run monitoring once")
    parser.add_argument("--report", action="store_true", help="Generate status report")
    parser.add_argument("--test-alert", action="store_true", help="Test alert system")

    args = parser.parse_args()

    # Load configuration
    config = MonitorConfig()

    # Initialize monitor
    monitor = VrittiMonitor(config)

    if args.report:
        # Generate and print status report
        report = monitor.generate_status_report()
        print(json.dumps(report, indent=2))
    elif args.test_alert:
        # Test alert system
        async def test_alert():
            await monitor.alert_manager.send_alert("TEST", "INFO", "Test alert from monitoring system")

        asyncio.run(test_alert())
        print("Test alert sent")
    elif args.once:
        # Run monitoring once
        asyncio.run(monitor.run_monitoring_cycle())
    else:
        # Run continuous monitoring
        asyncio.run(monitor.run_continuous_monitoring())


if __name__ == "__main__":
    main()

---

# scripts/health_check.py - Simple health check script
"""
Simple health check script for load balancers and uptime monitoring
"""

import requests
import sys
import time
import json


def check_health(url="http://localhost:8000", timeout=10):
    """Simple health check"""
    try:
        response = requests.get(f"{url}/", timeout=timeout)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print("✅ HEALTHY")
                return 0
            else:
                print("❌ UNHEALTHY - Invalid response")
                return 1
        else:
            print(f"❌ UNHEALTHY - HTTP {response.status_code}")
            return 1

    except requests.exceptions.RequestException as e:
        print(f"❌ UNHEALTHY - {e}")
        return 1


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    exit_code = check_health(url)
    sys.exit(exit_code)

---

# scripts/performance_monitor.py - Performance monitoring
"""
Performance monitoring and metrics collection
"""

import asyncio
import aiohttp
import time
import json
import statistics
from datetime import datetime
from typing import List, Dict, Any


class PerformanceMonitor:
    """Monitor API performance and collect metrics"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.metrics = []

    async def measure_endpoint_performance(self, endpoint: str, method: str = "GET",
                                           data: Dict = None, files: Dict = None) -> Dict[str, Any]:
        """Measure performance of a single endpoint"""
        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        response_time = time.time() - start_time
                        content = await response.text()

                        return {
                            "endpoint": endpoint,
                            "method": method,
                            "status_code": response.status,
                            "response_time": response_time,
                            "content_length": len(content),
                            "timestamp": datetime.now().isoformat(),
                            "success": response.status == 200
                        }
                elif method == "POST":
                    if files:
                        data_form = aiohttp.FormData()
                        for key, value in files.items():
                            data_form.add_field(key, value)

                        async with session.post(f"{self.base_url}{endpoint}",
                                                data=data_form) as response:
                            response_time = time.time() - start_time
                            content = await response.text()

                            return {
                                "endpoint": endpoint,
                                "method": method,
                                "status_code": response.status,
                                "response_time": response_time,
                                "content_length": len(content),
                                "timestamp": datetime.now().isoformat(),
                                "success": response.status == 200
                            }

        except Exception as e:
            return {
                "endpoint": endpoint,
                "method": method,
                "error": str(e),
                "response_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
                "success": False
            }

    async def run_performance_suite(self, iterations: int = 10):
        """Run comprehensive performance test suite"""
        print(f"🚀 Running performance test suite ({iterations} iterations)...")

        endpoints = [
            ("/", "GET"),
            ("/config", "GET"),
            ("/api/v1/mobile/dashboard", "GET"),
        ]

        # Test each endpoint
        for endpoint, method in endpoints:
            print(f"\n📊 Testing {method} {endpoint}")
            endpoint_metrics = []

            for i in range(iterations):
                metric = await self.measure_endpoint_performance(endpoint, method)
                endpoint_metrics.append(metric)

                if metric["success"]:
                    print(f"  Iteration {i + 1}: {metric['response_time']:.3f}s")
                else:
                    print(f"  Iteration {i + 1}: FAILED - {metric.get('error', 'Unknown error')}")

            # Calculate statistics
            successful_metrics = [m for m in endpoint_metrics if m["success"]]
            if successful_metrics:
                response_times = [m["response_time"] for m in successful_metrics]

                stats = {
                    "endpoint": endpoint,
                    "method": method,
                    "total_requests": len(endpoint_metrics),
                    "successful_requests": len(successful_metrics),
                    "success_rate": len(successful_metrics) / len(endpoint_metrics) * 100,
                    "avg_response_time": statistics.mean(response_times),
                    "min_response_time": min(response_times),
                    "max_response_time": max(response_times),
                    "median_response_time": statistics.median(response_times),
                    "p95_response_time": sorted(response_times)[int(0.95 * len(response_times))],
                }

                print(f"  📈 Results:")
                print(f"    Success Rate: {stats['success_rate']:.1f}%")
                print(f"    Average Response Time: {stats['avg_response_time']:.3f}s")
                print(f"    Min/Max: {stats['min_response_time']:.3f}s / {stats['max_response_time']:.3f}s")
                print(f"    95th Percentile: {stats['p95_response_time']:.3f}s")

                self.metrics.append(stats)
            else:
                print(f"  ❌ All requests failed for {endpoint}")

    def generate_performance_report(self) -> str:
        """Generate HTML performance report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Vritti AI Performance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .metric {{ margin: 15px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .good {{ border-left: 4px solid #28a745; }}
        .warning {{ border-left: 4px solid #ffc107; }}
        .critical {{ border-left: 4px solid #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Vritti AI Performance Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <h2>Performance Metrics Summary</h2>
    <table>
        <tr>
            <th>Endpoint</th>
            <th>Method</th>
            <th>Success Rate</th>
            <th>Avg Response Time</th>
            <th>95th Percentile</th>
            <th>Status</th>
        </tr>
        {''.join(self._format_metric_row(metric) for metric in self.metrics)}
    </table>
</body>
</html>
        """
        return html

    def _format_metric_row(self, metric: Dict[str, Any]) -> str:
        """Format metric row for HTML table"""
        # Determine status based on performance
        if metric['success_rate'] >= 99 and metric['avg_response_time'] <= 2.0:
            status = "✅ Excellent"
            css_class = "good"
        elif metric['success_rate'] >= 95 and metric['avg_response_time'] <= 5.0:
            status = "⚠️ Good"
            css_class = "warning"
        else:
            status = "❌ Poor"
            css_class = "critical"

        return f"""
        <tr class="{css_class}">
            <td>{metric['endpoint']}</td>
            <td>{metric['method']}</td>
            <td>{metric['success_rate']:.1f}%</td>
            <td>{metric['avg_response_time']:.3f}s</td>
            <td>{metric['p95_response_time']:.3f}s</td>
            <td>{status}</td>
        </tr>
        """


async def main():
    monitor = PerformanceMonitor()
    await monitor.run_performance_suite(iterations=20)

    # Generate report
    report = monitor.generate_performance_report()
    with open("performance_report.html", "w") as f:
        f.write(report)

    print("\n📊 Performance report generated: performance_report.html")


if __name__ == "__main__":
    asyncio.run(main())