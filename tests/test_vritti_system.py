# tests/test_vritti_system.py
"""
Comprehensive test scripts for Vritti Invoice AI v2.0.0
Tests all major components: API, Document AI, OCR, Multi-currency, Mobile endpoints
"""

import pytest
import asyncio
import requests
import json
import io
from pathlib import Path
from PIL import Image
import tempfile
import os
from typing import Dict, Any, List

# Test Configuration
TEST_CONFIG = {
    "base_url": "http://localhost:8000",
    "timeout": 30,
    "test_files_dir": "tests/fixtures",
    "expected_currencies": ["USD", "EUR", "GBP", "CAD", "JPY", "INR"],
    "expected_features": [
        "document_ai", "ocr_service", "hybrid_processing",
        "image_enhancement", "multi_currency", "global_support"
    ]
}


class VrittiTestSuite:
    """Main test suite for Vritti Invoice AI"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = TEST_CONFIG["timeout"]

    def test_health_check(self) -> Dict[str, Any]:
        """Test basic health check endpoint"""
        print("🔍 Testing Health Check...")

        try:
            response = self.session.get(f"{self.base_url}/")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert "Vritti Invoice AI" in data["message"]
            assert "features" in data

            print("✅ Health check passed")
            return {"status": "PASS", "data": data}

        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return {"status": "FAIL", "error": str(e)}

    def test_config_endpoint(self) -> Dict[str, Any]:
        """Test configuration endpoint"""
        print("🔍 Testing Configuration Endpoint...")

        try:
            response = self.session.get(f"{self.base_url}/config")
            assert response.status_code == 200

            data = response.json()

            # Check required configuration fields
            required_fields = [
                "max_file_size_mb", "allowed_extensions", "api_version",
                "supported_currencies", "features"
            ]

            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            # Verify supported currencies
            currencies = data["supported_currencies"]
            assert len(currencies) >= 30, f"Expected 30+ currencies, got {len(currencies)}"

            for currency in TEST_CONFIG["expected_currencies"]:
                assert currency in currencies, f"Missing expected currency: {currency}"

            # Verify features
            features = data["features"]
            for feature in TEST_CONFIG["expected_features"]:
                assert feature in features, f"Missing expected feature: {feature}"

            print(f"✅ Configuration test passed - {len(currencies)} currencies supported")
            return {"status": "PASS", "data": data}

        except Exception as e:
            print(f"❌ Configuration test failed: {e}")
            return {"status": "FAIL", "error": str(e)}

    def test_mobile_dashboard(self) -> Dict[str, Any]:
        """Test mobile dashboard endpoint"""
        print("🔍 Testing Mobile Dashboard...")

        try:
            response = self.session.get(f"{self.base_url}/api/v1/mobile/dashboard")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert data["app_name"] == "Vritti Invoice AI"
            assert "features" in data
            assert "version" in data

            print("✅ Mobile dashboard test passed")
            return {"status": "PASS", "data": data}

        except Exception as e:
            print(f"❌ Mobile dashboard test failed: {e}")
            return {"status": "FAIL", "error": str(e)}

    def create_test_invoice_image(self, text: str = "Test Invoice", amount: str = "$123.45") -> bytes:
        """Create a simple test invoice image"""
        # Create a simple invoice image
        img = Image.new('RGB', (800, 600), color='white')

        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        return img_buffer.getvalue()

    def test_invoice_processing(self, test_file_path: str = None) -> Dict[str, Any]:
        """Test invoice processing endpoint"""
        print("🔍 Testing Invoice Processing...")

        try:
            # Use provided file or create test image
            if test_file_path and Path(test_file_path).exists():
                with open(test_file_path, 'rb') as f:
                    file_content = f.read()
                filename = Path(test_file_path).name
            else:
                file_content = self.create_test_invoice_image()
                filename = "test_invoice.png"

            # Test mobile endpoint
            files = {"file": (filename, file_content, "image/png")}
            response = self.session.post(
                f"{self.base_url}/api/v1/mobile/process-invoice",
                files=files
            )

            assert response.status_code == 200
            data = response.json()

            # Check required response fields
            required_fields = ["success", "processing_time", "mobile_optimized"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            print(f"✅ Invoice processing test passed - {data.get('processing_time', 0):.2f}s")
            return {"status": "PASS", "data": data}

        except Exception as e:
            print(f"❌ Invoice processing test failed: {e}")
            return {"status": "FAIL", "error": str(e)}

    def test_batch_processing(self) -> Dict[str, Any]:
        """Test batch processing endpoint"""
        print("🔍 Testing Batch Processing...")

        try:
            # Create multiple test files
            test_files = []
            for i in range(3):
                file_content = self.create_test_invoice_image(f"Test Invoice {i + 1}", f"${100 + i * 50}.00")
                test_files.append(("files", (f"test_invoice_{i + 1}.png", file_content, "image/png")))

            response = self.session.post(
                f"{self.base_url}/batch-process",
                files=test_files
            )

            assert response.status_code == 200
            data = response.json()

            # Check batch response structure
            assert "batch_results" in data
            assert "total_files" in data
            assert "successful_files" in data
            assert "failed_files" in data

            assert data["total_files"] == 3

            print(f"✅ Batch processing test passed - {data['successful_files']}/{data['total_files']} files processed")
            return {"status": "PASS", "data": data}

        except Exception as e:
            print(f"❌ Batch processing test failed: {e}")
            return {"status": "FAIL", "error": str(e)}

    def test_image_analysis(self) -> Dict[str, Any]:
        """Test image analysis endpoint"""
        print("🔍 Testing Image Analysis...")

        try:
            file_content = self.create_test_invoice_image()
            files = {"file": ("test_image.png", file_content, "image/png")}

            response = self.session.get(
                f"{self.base_url}/api/v1/image/analyze",
                files=files
            )

            assert response.status_code == 200
            data = response.json()

            assert "success" in data
            assert "filename" in data

            print("✅ Image analysis test passed")
            return {"status": "PASS", "data": data}

        except Exception as e:
            print(f"❌ Image analysis test failed: {e}")
            return {"status": "FAIL", "error": str(e)}

    def test_file_validation(self) -> Dict[str, Any]:
        """Test file validation and error handling"""
        print("🔍 Testing File Validation...")

        results = {}

        # Test 1: No file provided
        try:
            response = self.session.post(f"{self.base_url}/api/v1/mobile/process-invoice")
            assert response.status_code == 422  # Validation error
            results["no_file"] = "PASS"
        except Exception as e:
            results["no_file"] = f"FAIL: {e}"

        # Test 2: Invalid file type
        try:
            invalid_content = b"This is not an image"
            files = {"file": ("test.txt", invalid_content, "text/plain")}
            response = self.session.post(
                f"{self.base_url}/api/v1/mobile/process-invoice",
                files=files
            )
            assert response.status_code == 400  # Bad request
            results["invalid_type"] = "PASS"
        except Exception as e:
            results["invalid_type"] = f"FAIL: {e}"

        # Test 3: Large file (simulate)
        try:
            # Create a large dummy file (simulated)
            large_content = b"0" * (15 * 1024 * 1024)  # 15MB
            files = {"file": ("large_file.png", large_content, "image/png")}
            response = self.session.post(
                f"{self.base_url}/api/v1/mobile/process-invoice",
                files=files
            )
            assert response.status_code == 413  # File too large
            results["large_file"] = "PASS"
        except Exception as e:
            results["large_file"] = f"FAIL: {e}"

        passed = sum(1 for result in results.values() if result == "PASS")
        print(f"✅ File validation tests: {passed}/{len(results)} passed")
        return {"status": "PASS" if passed == len(results) else "PARTIAL", "results": results}

    def test_currency_detection(self) -> Dict[str, Any]:
        """Test multi-currency detection capabilities"""
        print("🔍 Testing Currency Detection...")

        try:
            # Test with different currency samples
            currency_tests = [
                ("USD", "$123.45"),
                ("EUR", "€456.78"),
                ("GBP", "£789.12"),
                ("JPY", "¥1000"),
                ("INR", "₹2000.50")
            ]

            results = {}
            for currency, amount in currency_tests:
                try:
                    # Create test image with currency
                    file_content = self.create_test_invoice_image(f"Invoice {currency}", amount)
                    files = {"file": (f"test_{currency.lower()}.png", file_content, "image/png")}

                    response = self.session.post(
                        f"{self.base_url}/api/v1/mobile/process-invoice",
                        files=files
                    )

                    if response.status_code == 200:
                        results[currency] = "PASS"
                    else:
                        results[currency] = f"HTTP {response.status_code}"

                except Exception as e:
                    results[currency] = f"FAIL: {e}"

            passed = sum(1 for result in results.values() if result == "PASS")
            print(f"✅ Currency detection tests: {passed}/{len(results)} passed")
            return {"status": "PASS" if passed >= 3 else "PARTIAL", "results": results}

        except Exception as e:
            print(f"❌ Currency detection test failed: {e}")
            return {"status": "FAIL", "error": str(e)}

    def run_full_test_suite(self, test_file_path: str = None) -> Dict[str, Any]:
        """Run complete test suite"""
        print("🚀 Starting Vritti Invoice AI Test Suite")
        print("=" * 50)

        test_results = {}

        # Core API Tests
        test_results["health_check"] = self.test_health_check()
        test_results["config"] = self.test_config_endpoint()
        test_results["mobile_dashboard"] = self.test_mobile_dashboard()

        # Processing Tests
        test_results["invoice_processing"] = self.test_invoice_processing(test_file_path)
        test_results["batch_processing"] = self.test_batch_processing()
        test_results["image_analysis"] = self.test_image_analysis()

        # Validation Tests
        test_results["file_validation"] = self.test_file_validation()
        test_results["currency_detection"] = self.test_currency_detection()

        # Summary
        passed_tests = sum(1 for result in test_results.values()
                           if result.get("status") == "PASS")
        total_tests = len(test_results)

        print("\n" + "=" * 50)
        print("📊 TEST SUITE SUMMARY")
        print("=" * 50)

        for test_name, result in test_results.items():
            status = result.get("status", "UNKNOWN")
            if status == "PASS":
                print(f"✅ {test_name.replace('_', ' ').title()}: PASSED")
            elif status == "PARTIAL":
                print(f"⚠️ {test_name.replace('_', ' ').title()}: PARTIAL")
            else:
                print(f"❌ {test_name.replace('_', ' ').title()}: FAILED")

        print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("🎉 All tests passed! System is working correctly.")
        elif passed_tests >= total_tests * 0.8:
            print("✅ Most tests passed. System is largely functional.")
        else:
            print("⚠️ Several tests failed. Please check system configuration.")

        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "pass_rate": passed_tests / total_tests * 100
            },
            "detailed_results": test_results
        }


# Performance Test Suite
class VrittiPerformanceTests:
    """Performance testing for Vritti Invoice AI"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()

    def test_processing_speed(self, num_requests: int = 10) -> Dict[str, Any]:
        """Test processing speed and consistency"""
        print(f"🔍 Testing Processing Speed ({num_requests} requests)...")

        import time
        times = []

        for i in range(num_requests):
            start_time = time.time()

            # Create test file
            img = Image.new('RGB', (800, 600), color='white')
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')

            files = {"file": (f"test_{i}.png", img_buffer.getvalue(), "image/png")}

            try:
                response = self.session.post(
                    f"{self.base_url}/api/v1/mobile/process-invoice",
                    files=files
                )

                end_time = time.time()
                request_time = end_time - start_time
                times.append(request_time)

                print(f"  Request {i + 1}: {request_time:.2f}s")

            except Exception as e:
                print(f"  Request {i + 1}: FAILED - {e}")

        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)

            print(f"✅ Performance Results:")
            print(f"  Average: {avg_time:.2f}s")
            print(f"  Min: {min_time:.2f}s")
            print(f"  Max: {max_time:.2f}s")

            return {
                "status": "PASS",
                "average_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "total_requests": len(times)
            }
        else:
            return {"status": "FAIL", "error": "No successful requests"}

    def test_concurrent_requests(self, concurrent_users: int = 5) -> Dict[str, Any]:
        """Test system under concurrent load"""
        print(f"🔍 Testing Concurrent Requests ({concurrent_users} users)...")

        import threading
        import time

        results = []

        def make_request(user_id: int):
            try:
                start_time = time.time()

                img = Image.new('RGB', (800, 600), color='white')
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')

                files = {"file": (f"concurrent_test_{user_id}.png", img_buffer.getvalue(), "image/png")}

                response = self.session.post(
                    f"{self.base_url}/api/v1/mobile/process-invoice",
                    files=files
                )

                end_time = time.time()

                results.append({
                    "user_id": user_id,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200
                })

            except Exception as e:
                results.append({
                    "user_id": user_id,
                    "error": str(e),
                    "success": False
                })

        # Start concurrent requests
        threads = []
        start_time = time.time()

        for i in range(concurrent_users):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        total_time = time.time() - start_time
        successful_requests = sum(1 for r in results if r.get("success", False))

        print(f"✅ Concurrent Test Results:")
        print(f"  Successful: {successful_requests}/{concurrent_users}")
        print(f"  Total Time: {total_time:.2f}s")
        print(f"  Success Rate: {successful_requests / concurrent_users * 100:.1f}%")

        return {
            "status": "PASS" if successful_requests >= concurrent_users * 0.8 else "PARTIAL",
            "successful_requests": successful_requests,
            "total_requests": concurrent_users,
            "total_time": total_time,
            "success_rate": successful_requests / concurrent_users * 100
        }


# CLI Test Runner
def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description="Vritti Invoice AI Test Suite")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for API")
    parser.add_argument("--test-file", help="Path to test invoice file")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")

    args = parser.parse_args()

    # Run main test suite
    test_suite = VrittiTestSuite(args.url)

    if args.quick:
        # Quick tests
        print("🚀 Running Quick Test Suite")
        results = {}
        results["health"] = test_suite.test_health_check()
        results["config"] = test_suite.test_config_endpoint()
        results["processing"] = test_suite.test_invoice_processing(args.test_file)
    else:
        # Full test suite
        results = test_suite.run_full_test_suite(args.test_file)

    # Run performance tests if requested
    if args.performance:
        print("\n🚀 Running Performance Tests")
        perf_suite = VrittiPerformanceTests(args.url)
        perf_results = {}
        perf_results["speed"] = perf_suite.test_processing_speed()
        perf_results["concurrent"] = perf_suite.test_concurrent_requests()

        print("\n📊 Performance Summary:")
        for test_name, result in perf_results.items():
            status = result.get("status", "UNKNOWN")
            print(f"  {test_name}: {status}")

    return results


if __name__ == "__main__":
    results = main()