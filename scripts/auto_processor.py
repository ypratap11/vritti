# scripts/auto_processor.py - Automated file processing system
"""
Automated invoice processing system that watches directories,
processes files, and manages workflows
"""

import asyncio
import aiohttp
import aiofiles
import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import schedule
from concurrent.futures import ThreadPoolExecutor


# Configuration
@dataclass
class ProcessorConfig:
    # Directories
    watch_directory: str = "input"
    processing_directory: str = "processing"
    completed_directory: str = "completed"
    failed_directory: str = "failed"
    archive_directory: str = "archive"

    # API settings
    api_url: str = "http://localhost:8000"
    api_timeout: int = 300  # 5 minutes

    # Processing settings
    batch_size: int = 5
    max_concurrent: int = 3
    retry_attempts: int = 3
    retry_delay: int = 30  # seconds

    # File settings
    supported_extensions: List[str] = None
    max_file_size: int = 50 * 1024 * 1024  # 50MB

    # Scheduling
    cleanup_schedule: str = "02:00"  # 2 AM daily
    archive_after_days: int = 30

    # Notifications
    webhook_url: Optional[str] = None
    email_notifications: bool = False

    def __post_init__(self):
        if self.supported_extensions is None:
            self.supported_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.gif']

        # Create directories
        for directory in [self.watch_directory, self.processing_directory,
                          self.completed_directory, self.failed_directory,
                          self.archive_directory]:
            Path(directory).mkdir(exist_ok=True)


@dataclass
class ProcessingResult:
    file_path: str
    status: str  # SUCCESS, FAILED, RETRY
    processing_time: float
    api_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class FileProcessor:
    """Handles individual file processing"""

    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.logger = logging.getLogger("FileProcessor")

    async def process_file(self, file_path: Path) -> ProcessingResult:
        """Process a single file"""
        start_time = time.time()

        try:
            # Validate file
            validation_error = self._validate_file(file_path)
            if validation_error:
                return ProcessingResult(
                    file_path=str(file_path),
                    status="FAILED",
                    processing_time=time.time() - start_time,
                    error_message=validation_error
                )

            # Move to processing directory
            processing_path = Path(self.config.processing_directory) / file_path.name
            shutil.move(str(file_path), str(processing_path))

            # Process via API
            result = await self._process_via_api(processing_path)

            # Move to appropriate directory based on result
            if result.status == "SUCCESS":
                final_path = Path(self.config.completed_directory) / processing_path.name
                shutil.move(str(processing_path), str(final_path))

                # Save processing result
                await self._save_result(final_path, result)
            else:
                failed_path = Path(self.config.failed_directory) / processing_path.name
                shutil.move(str(processing_path), str(failed_path))

            return result

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            return ProcessingResult(
                file_path=str(file_path),
                status="FAILED",
                processing_time=time.time() - start_time,
                error_message=str(e)
            )

    def _validate_file(self, file_path: Path) -> Optional[str]:
        """Validate file before processing"""
        # Check if file exists
        if not file_path.exists():
            return "File does not exist"

        # Check file extension
        if file_path.suffix.lower() not in self.config.supported_extensions:
            return f"Unsupported file type: {file_path.suffix}"

        # Check file size
        if file_path.stat().st_size > self.config.max_file_size:
            return f"File too large: {file_path.stat().st_size} bytes"

        # Check if file is not empty
        if file_path.stat().st_size == 0:
            return "File is empty"

        return None

    async def _process_via_api(self, file_path: Path) -> ProcessingResult:
        """Process file via API"""
        start_time = time.time()

        try:
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()

            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', file_content,
                               filename=file_path.name,
                               content_type=self._get_content_type(file_path))

                async with session.post(
                        f"{self.config.api_url}/api/v1/mobile/process-invoice",
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=self.config.api_timeout)
                ) as response:

                    processing_time = time.time() - start_time

                    if response.status == 200:
                        api_response = await response.json()
                        return ProcessingResult(
                            file_path=str(file_path),
                            status="SUCCESS",
                            processing_time=processing_time,
                            api_response=api_response
                        )
                    else:
                        error_text = await response.text()
                        return ProcessingResult(
                            file_path=str(file_path),
                            status="FAILED",
                            processing_time=processing_time,
                            error_message=f"API error {response.status}: {error_text}"
                        )

        except asyncio.TimeoutError:
            return ProcessingResult(
                file_path=str(file_path),
                status="RETRY",
                processing_time=time.time() - start_time,
                error_message="Request timeout"
            )
        except Exception as e:
            return ProcessingResult(
                file_path=str(file_path),
                status="FAILED",
                processing_time=time.time() - start_time,
                error_message=str(e)
            )

    def _get_content_type(self, file_path: Path) -> str:
        """Get content type for file"""
        extension = file_path.suffix.lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.tiff': 'image/tiff',
            '.gif': 'image/gif'
        }
        return content_types.get(extension, 'application/octet-stream')

    async def _save_result(self, file_path: Path, result: ProcessingResult):
        """Save processing result as JSON"""
        result_path = file_path.with_suffix('.json')

        result_data = asdict(result)
        result_data['timestamp'] = result.timestamp.isoformat()

        async with aiofiles.open(result_path, 'w') as f:
            await f.write(json.dumps(result_data, indent=2))


class FileWatcher(FileSystemEventHandler):
    """Watches directory for new files"""

    def __init__(self, processor_queue: asyncio.Queue):
        self.processor_queue = processor_queue
        self.logger = logging.getLogger("FileWatcher")

    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory:
            file_path = Path(event.src_path)

            # Wait a bit to ensure file is fully written
            time.sleep(2)

            if file_path.exists():
                self.logger.info(f"New file detected: {file_path}")
                try:
                    # Add to processing queue (non-blocking)
                    self.processor_queue.put_nowait(file_path)
                except asyncio.QueueFull:
                    self.logger.warning(f"Processing queue full, skipping: {file_path}")


class BatchProcessor:
    """Handles batch processing of files"""

    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.file_processor = FileProcessor(config)
        self.processing_queue = asyncio.Queue(maxsize=100)
        self.results = []
        self.logger = logging.getLogger("BatchProcessor")

    async def process_batch(self, file_paths: List[Path]) -> List[ProcessingResult]:
        """Process a batch of files concurrently"""
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def process_with_semaphore(file_path):
            async with semaphore:
                return await self.file_processor.process_file(file_path)

        tasks = [process_with_semaphore(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Exception processing {file_paths[i]}: {result}")
                processed_results.append(ProcessingResult(
                    file_path=str(file_paths[i]),
                    status="FAILED",
                    processing_time=0,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results

    async def process_queue_worker(self):
        """Worker that processes files from the queue"""
        batch = []

        while True:
            try:
                # Wait for files or timeout to process current batch
                try:
                    file_path = await asyncio.wait_for(
                        self.processing_queue.get(),
                        timeout=10.0
                    )
                    batch.append(file_path)
                except asyncio.TimeoutError:
                    pass

                # Process batch if it's full or we have files and timeout occurred
                if len(batch) >= self.config.batch_size or (batch and len(batch) > 0):
                    self.logger.info(f"Processing batch of {len(batch)} files")

                    results = await self.process_batch(batch)
                    self.results.extend(results)

                    # Log results
                    successful = sum(1 for r in results if r.status == "SUCCESS")
                    failed = sum(1 for r in results if r.status == "FAILED")
                    retry = sum(1 for r in results if r.status == "RETRY")

                    self.logger.info(f"Batch completed: {successful} success, {failed} failed, {retry} retry")

                    # Handle retries
                    await self._handle_retries(results)

                    # Send notifications
                    await self._send_batch_notification(results)

                    batch = []

            except Exception as e:
                self.logger.error(f"Error in queue worker: {e}")
                await asyncio.sleep(5)

    async def _handle_retries(self, results: List[ProcessingResult]):
        """Handle files that need retry"""
        retry_files = [r for r in results if r.status == "RETRY"]

        if retry_files:
            self.logger.info(f"Scheduling {len(retry_files)} files for retry")

            async def retry_later():
                await asyncio.sleep(self.config.retry_delay)
                for result in retry_files:
                    file_path = Path(result.file_path)
                    if file_path.exists():
                        await self.processing_queue.put(file_path)

            # Schedule retry in background
            asyncio.create_task(retry_later())

    async def _send_batch_notification(self, results: List[ProcessingResult]):
        """Send notification about batch processing results"""
        if not self.config.webhook_url:
            return

        successful = sum(1 for r in results if r.status == "SUCCESS")
        failed = sum(1 for r in results if r.status == "FAILED")

        message = f"📊 Batch Processing Complete\n"
        message += f"✅ Successful: {successful}\n"
        message += f"❌ Failed: {failed}\n"
        message += f"⏱️ Total files: {len(results)}"

        try:
            async with aiohttp.ClientSession() as session:
                payload = {"text": message}
                await session.post(self.config.webhook_url, json=payload)
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")


class ArchiveManager:
    """Manages archiving and cleanup of processed files"""

    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.logger = logging.getLogger("ArchiveManager")

    def cleanup_old_files(self):
        """Clean up old files based on configuration"""
        cutoff_date = datetime.now() - timedelta(days=self.config.archive_after_days)

        directories_to_clean = [
            self.config.completed_directory,
            self.config.failed_directory
        ]

        for directory in directories_to_clean:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue

            for file_path in dir_path.glob("*"):
                if file_path.is_file():
                    # Check file modification time
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)

                    if file_time < cutoff_date:
                        # Move to archive
                        archive_path = Path(self.config.archive_directory) / file_path.name

                        try:
                            shutil.move(str(file_path), str(archive_path))
                            self.logger.info(f"Archived: {file_path}")
                        except Exception as e:
                            self.logger.error(f"Failed to archive {file_path}: {e}")

    def generate_processing_report(self) -> Dict[str, Any]:
        """Generate processing statistics report"""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "directories": {},
            "recent_activity": {}
        }

        # Count files in each directory
        directories = [
            self.config.watch_directory,
            self.config.processing_directory,
            self.config.completed_directory,
            self.config.failed_directory,
            self.config.archive_directory
        ]

        for directory in directories:
            dir_path = Path(directory)
            if dir_path.exists():
                files = list(dir_path.glob("*"))
                stats["directories"][directory] = {
                    "file_count": len([f for f in files if f.is_file()]),
                    "total_size": sum(f.stat().st_size for f in files if f.is_file())
                }

        # Analyze recent processing results
        completed_dir = Path(self.config.completed_directory)
        if completed_dir.exists():
            recent_results = []
            for json_file in completed_dir.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        result_data = json.load(f)
                        recent_results.append(result_data)
                except Exception as e:
                    self.logger.error(f"Error reading result file {json_file}: {e}")

            if recent_results:
                processing_times = [r.get("processing_time", 0) for r in recent_results]
                stats["recent_activity"] = {
                    "total_processed": len(recent_results),
                    "avg_processing_time": sum(processing_times) / len(processing_times),
                    "min_processing_time": min(processing_times),
                    "max_processing_time": max(processing_times)
                }

        return stats


class AutoProcessor:
    """Main automation processor class"""

    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.batch_processor = BatchProcessor(config)
        self.archive_manager = ArchiveManager(config)
        self.observer = None
        self.logger = logging.getLogger("AutoProcessor")

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('auto_processor.log'),
                logging.StreamHandler()
            ]
        )

    def start_file_watcher(self):
        """Start watching for new files"""
        file_watcher = FileWatcher(self.batch_processor.processing_queue)

        self.observer = Observer()
        self.observer.schedule(file_watcher, self.config.watch_directory, recursive=False)
        self.observer.start()

        self.logger.info(f"Started watching directory: {self.config.watch_directory}")

    def setup_scheduler(self):
        """Setup scheduled tasks"""
        # Schedule daily cleanup
        schedule.every().day.at(self.config.cleanup_schedule).do(
            self.archive_manager.cleanup_old_files
        )

        # Schedule daily reports
        schedule.every().day.at("08:00").do(self._send_daily_report)

        self.logger.info("Scheduled tasks configured")

    def _send_daily_report(self):
        """Send daily processing report"""
        try:
            report = self.archive_manager.generate_processing_report()

            if self.config.webhook_url:
                message = f"📊 Daily Processing Report\n"
                message += f"📁 Files in queue: {report['directories'].get(self.config.watch_directory, {}).get('file_count', 0)}\n"
                message += f"✅ Completed: {report['directories'].get(self.config.completed_directory, {}).get('file_count', 0)}\n"
                message += f"❌ Failed: {report['directories'].get(self.config.failed_directory, {}).get('file_count', 0)}\n"

                if report.get('recent_activity'):
                    activity = report['recent_activity']
                    message += f"⏱️ Avg processing time: {activity.get('avg_processing_time', 0):.2f}s"

                # Send async notification
                asyncio.create_task(self._send_webhook_notification(message))

        except Exception as e:
            self.logger.error(f"Error generating daily report: {e}")

    async def _send_webhook_notification(self, message: str):
        """Send webhook notification"""
        if not self.config.webhook_url:
            return

        try:
            async with aiohttp.ClientSession() as session:
                payload = {"text": message}
                await session.post(self.config.webhook_url, json=payload)
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")

    async def run(self):
        """Run the auto processor"""
        self.logger.info("🚀 Starting Vritti Auto Processor...")

        # Start file watcher
        self.start_file_watcher()

        # Setup scheduler
        self.setup_scheduler()

        # Start queue worker
        queue_worker_task = asyncio.create_task(
            self.batch_processor.process_queue_worker()
        )

        # Run scheduler in background
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        scheduler_executor = ThreadPoolExecutor(max_workers=1)
        scheduler_task = asyncio.get_event_loop().run_in_executor(
            scheduler_executor, run_scheduler
        )

        self.logger.info("✅ Auto processor started successfully")

        try:
            # Wait for tasks
            await asyncio.gather(queue_worker_task, scheduler_task)
        except KeyboardInterrupt:
            self.logger.info("Shutting down auto processor...")
        finally:
            if self.observer:
                self.observer.stop()
                self.observer.join()
            scheduler_executor.shutdown(wait=True)


# CLI for the auto processor
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Vritti Invoice AI Auto Processor")
    parser.add_argument("--watch-dir", default="input", help="Directory to watch for new files")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--batch-size", type=int, default=5, help="Batch size for processing")
    parser.add_argument("--webhook-url", help="Webhook URL for notifications")
    parser.add_argument("--report", action="store_true", help="Generate report only")
    parser.add_argument("--cleanup", action="store_true", help="Run cleanup only")

    args = parser.parse_args()

    # Create configuration
    config = ProcessorConfig(
        watch_directory=args.watch_dir,
        api_url=args.api_url,
        batch_size=args.batch_size,
        webhook_url=args.webhook_url
    )

    if args.report:
        # Generate report only
        archive_manager = ArchiveManager(config)
        report = archive_manager.generate_processing_report()
        print(json.dumps(report, indent=2))
    elif args.cleanup:
        # Run cleanup only
        archive_manager = ArchiveManager(config)
        archive_manager.cleanup_old_files()
        print("Cleanup completed")
    else:
        # Run auto processor
        processor = AutoProcessor(config)
        asyncio.run(processor.run())


if __name__ == "__main__":
    main()

---

# scripts/bulk_processor.py - Process existing files in bulk
"""
Bulk processor for existing invoice files
"""

import asyncio
import aiohttp
import aiofiles
import json
from pathlib import Path
from typing import List, Dict, Any
import time


class BulkProcessor:
    """Process multiple existing files in bulk"""

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.results = []

    async def process_directory(self, directory: str, output_dir: str = "bulk_results"):
        """Process all supported files in a directory"""
        input_path = Path(directory)
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Find all supported files
        supported_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.gif']
        files = []

        for ext in supported_extensions:
            files.extend(input_path.glob(f"*{ext}"))
            files.extend(input_path.glob(f"*{ext.upper()}"))

        print(f"Found {len(files)} files to process in {directory}")

        if not files:
            print("No supported files found")
            return

        # Process files
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests

        async def process_file_with_semaphore(file_path):
            async with semaphore:
                return await self._process_single_file(file_path, output_path)

        tasks = [process_file_with_semaphore(f) for f in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful = 0
        failed = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ {files[i].name}: {result}")
                failed += 1
            elif result['status'] == 'success':
                print(f"✅ {files[i].name}: {result['processing_time']:.2f}s")
                successful += 1
            else:
                print(f"❌ {files[i].name}: {result['error']}")
                failed += 1

        print(f"\n📊 Bulk processing completed:")
        print(f"  ✅ Successful: {successful}")
        print(f"  ❌ Failed: {failed}")
        print(f"  📁 Results saved to: {output_path}")

        # Generate summary report
        await self._generate_summary_report(output_path, results, files)

    async def _process_single_file(self, file_path: Path, output_dir: Path) -> Dict[str, Any]:
        """Process a single file"""
        start_time = time.time()

        try:
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()

            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', file_content, filename=file_path.name)

                async with session.post(
                        f"{self.api_url}/api/v1/mobile/process-invoice",
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=300)
                ) as response:

                    processing_time = time.time() - start_time

                    if response.status == 200:
                        result = await response.json()

                        # Save individual result
                        result_file = output_dir / f"{file_path.stem}_result.json"
                        async with aiofiles.open(result_file, 'w') as f:
                            await f.write(json.dumps(result, indent=2))

                        return {
                            'status': 'success',
                            'file': file_path.name,
                            'processing_time': processing_time,
                            'result': result
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'status': 'failed',
                            'file': file_path.name,
                            'processing_time': processing_time,
                            'error': f"HTTP {response.status}: {error_text}"
                        }

        except Exception as e:
            return {
                'status': 'failed',
                'file': file_path.name,
                'processing_time': time.time() - start_time,
                'error': str(e)
            }

    async def _generate_summary_report(self, output_dir: Path, results: List, files: List[Path]):
        """Generate summary report"""
        summary = {
            'timestamp': time.time(),
            'total_files': len(files),
            'successful': sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success'),
            'failed': sum(1 for r in results if
                          isinstance(r, Exception) or (isinstance(r, dict) and r.get('status') == 'failed')),
            'total_processing_time': sum(r.get('processing_time', 0) for r in results if isinstance(r, dict)),
            'files': []
        }

        for i, result in enumerate(results):
            if isinstance(result, dict):
                summary['files'].append({
                    'filename': files[i].name,
                    'status': result['status'],
                    'processing_time': result['processing_time'],
                    'error': result.get('error')
                })
            else:
                summary['files'].append({
                    'filename': files[i].name,
                    'status': 'failed',
                    'processing_time': 0,
                    'error': str(result)
                })

        # Save summary
        summary_file = output_dir / 'bulk_processing_summary.json'
        async with aiofiles.open(summary_file, 'w') as f:
            await f.write(json.dumps(summary, indent=2))

        print(f"📊 Summary report saved: {summary_file}")


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Bulk process invoice files")
    parser.add_argument("directory", help="Directory containing invoice files")
    parser.add_argument("--output", default="bulk_results", help="Output directory for results")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL")

    args = parser.parse_args()

    processor = BulkProcessor(args.api_url)
    await processor.process_directory(args.directory, args.output)


if __name__ == "__main__":
    asyncio.run(main())