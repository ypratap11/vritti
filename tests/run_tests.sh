#!/bin/bash
# run_tests.sh - Test runner script for Vritti Invoice AI

echo "🚀 Vritti Invoice AI Test Suite Runner"
echo "======================================"

# Configuration
BASE_URL=${BASE_URL:-"http://localhost:8000"}
TEST_FILES_DIR=${TEST_FILES_DIR:-"tests/test_files"}
PYTHON_CMD=${PYTHON_CMD:-"python"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    case $2 in
        "SUCCESS") echo -e "${GREEN}✅ $1${NC}" ;;
        "ERROR") echo -e "${RED}❌ $1${NC}" ;;
        "WARNING") echo -e "${YELLOW}⚠️ $1${NC}" ;;
        "INFO") echo -e "${BLUE}ℹ️ $1${NC}" ;;
        *) echo "$1" ;;
    esac
}

# Check if server is running
check_server() {
    print_status "Checking if Vritti server is running..." "INFO"

    if curl -s "$BASE_URL" > /dev/null 2>&1; then
        print_status "Server is running at $BASE_URL" "SUCCESS"
        return 0
    else
        print_status "Server is not running at $BASE_URL" "ERROR"
        echo "Please start the server with: uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
        return 1
    fi
}

# Install test dependencies
install_dependencies() {
    print_status "Installing test dependencies..." "INFO"

    if command -v pip &> /dev/null; then
        pip install requests pillow pytest > /dev/null 2>&1
        print_status "Dependencies installed" "SUCCESS"
    else
        print_status "pip not found. Please install dependencies manually" "WARNING"
    fi
}

# Create test files directory
setup_test_files() {
    print_status "Setting up test files directory..." "INFO"

    mkdir -p "$TEST_FILES_DIR"

    # Create a simple test invoice image using Python
    cat > "$TEST_FILES_DIR/create_test_image.py" << 'EOF'
from PIL import Image, ImageDraw, ImageFont
import sys

def create_test_invoice():
    # Create a simple invoice image
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)

    # Try to use a default font
    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_medium = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw invoice content
    draw.text((50, 50), "TEST COMPANY INC", fill='black', font=font_large)
    draw.text((50, 80), "123 Test Street, Test City, TC 12345", fill='black', font=font_small)
    draw.text((50, 100), "Phone: (555) 123-4567", fill='black', font=font_small)

    draw.text((50, 150), "INVOICE", fill='black', font=font_large)
    draw.text((50, 180), "Invoice #: INV-2024-001", fill='black', font=font_medium)
    draw.text((50, 200), "Date: March 13, 2024", fill='black', font=font_medium)

    draw.text((50, 250), "Bill To:", fill='black', font=font_medium)
    draw.text((50, 270), "Customer Name", fill='black', font=font_small)
    draw.text((50, 290), "456 Customer Ave", fill='black', font=font_small)
    draw.text((50, 310), "Customer City, CC 67890", fill='black', font=font_small)

    # Line items
    draw.text((50, 360), "Description", fill='black', font=font_medium)
    draw.text((400, 360), "Qty", fill='black', font=font_medium)
    draw.text((500, 360), "Price", fill='black', font=font_medium)
    draw.text((600, 360), "Total", fill='black', font=font_medium)

    draw.line([(50, 380), (700, 380)], fill='black', width=1)

    draw.text((50, 400), "Professional Services", fill='black', font=font_small)
    draw.text((400, 400), "10", fill='black', font=font_small)
    draw.text((500, 400), "$100.00", fill='black', font=font_small)
    draw.text((600, 400), "$1,000.00", fill='black', font=font_small)

    draw.text((50, 420), "Software License", fill='black', font=font_small)
    draw.text((400, 420), "1", fill='black', font=font_small)
    draw.text((500, 420), "$500.00", fill='black', font=font_small)
    draw.text((600, 420), "$500.00", fill='black', font=font_small)

    # Totals
    draw.line([(400, 460), (700, 460)], fill='black', width=1)
    draw.text((450, 480), "Subtotal:", fill='black', font=font_medium)
    draw.text((600, 480), "$1,500.00", fill='black', font=font_medium)

    draw.text((450, 500), "Tax (8.5%):", fill='black', font=font_medium)
    draw.text((600, 500), "$127.50", fill='black', font=font_medium)

    draw.text((450, 520), "Total Amount:", fill='black', font=font_large)
    draw.text((600, 520), "$1,627.50", fill='black', font=font_large)

    # Save the image
    img.save(sys.argv[1] if len(sys.argv) > 1 else 'test_invoice.png')
    print("Test invoice image created")

if __name__ == "__main__":
    create_test_invoice()
EOF

    if command -v python &> /dev/null; then
        python "$TEST_FILES_DIR/create_test_image.py" "$TEST_FILES_DIR/test_invoice.png"
        print_status "Test invoice image created" "SUCCESS"
    else
        print_status "Python not found. Skipping test image creation" "WARNING"
    fi
}

# Run quick health check
run_quick_test() {
    print_status "Running quick health check..." "INFO"

    # Test health endpoint
    if curl -s "$BASE_URL" | grep -q "healthy"; then
        print_status "Health check passed" "SUCCESS"
    else
        print_status "Health check failed" "ERROR"
        return 1
    fi

    # Test config endpoint
    if curl -s "$BASE_URL/config" | grep -q "supported_currencies"; then
        print_status "Config endpoint working" "SUCCESS"
    else
        print_status "Config endpoint failed" "ERROR"
        return 1
    fi

    # Test mobile dashboard
    if curl -s "$BASE_URL/api/v1/mobile/dashboard" | grep -q "Vritti"; then
        print_status "Mobile dashboard working" "SUCCESS"
    else
        print_status "Mobile dashboard failed" "ERROR"
        return 1
    fi

    return 0
}

# Run full Python test suite
run_full_tests() {
    print_status "Running full Python test suite..." "INFO"

    # Check if test file exists
    TEST_FILE=""
    if [ -f "$TEST_FILES_DIR/test_invoice.png" ]; then
        TEST_FILE="--test-file $TEST_FILES_DIR/test_invoice.png"
    fi

    # Run the Python test suite
    if $PYTHON_CMD tests/test_vritti_system.py --url "$BASE_URL" $TEST_FILE; then
        print_status "Full test suite completed" "SUCCESS"
    else
        print_status "Some tests failed" "WARNING"
    fi
}

# Run performance tests
run_performance_tests() {
    print_status "Running performance tests..." "INFO"

    $PYTHON_CMD tests/test_vritti_system.py --url "$BASE_URL" --performance
}

# Test specific invoice file
test_invoice_file() {
    if [ -z "$1" ]; then
        print_status "No file specified for testing" "ERROR"
        return 1
    fi

    if [ ! -f "$1" ]; then
        print_status "File not found: $1" "ERROR"
        return 1
    fi

    print_status "Testing invoice file: $1" "INFO"

    # Use curl to test file upload
    response=$(curl -s -X POST "$BASE_URL/api/v1/mobile/process-invoice" \
        -F "file=@$1" \
        -w "%{http_code}")

    http_code="${response: -3}"

    if [ "$http_code" = "200" ]; then
        print_status "Invoice processing successful" "SUCCESS"
        echo "Response: ${response%???}" | jq . 2>/dev/null || echo "${response%???}"
    else
        print_status "Invoice processing failed (HTTP $http_code)" "ERROR"
        echo "Response: ${response%???}"
    fi
}

# Main menu
show_menu() {
    echo ""
    echo "Available test options:"
    echo "  1) Quick health check"
    echo "  2) Full test suite"
    echo "  3) Performance tests"
    echo "  4) Test specific invoice file"
    echo "  5) Setup test environment"
    echo "  6) All tests (setup + full + performance)"
    echo "  q) Quit"
    echo ""
}

# Main script logic
main() {
    # Parse command line arguments
    case "${1:-}" in
        "quick"|"health")
            check_server && run_quick_test
            ;;
        "full")
            check_server && run_full_tests
            ;;
        "performance"|"perf")
            check_server && run_performance_tests
            ;;
        "setup")
            install_dependencies
            setup_test_files
            ;;
        "all")
            install_dependencies
            setup_test_files
            check_server && run_full_tests && run_performance_tests
            ;;
        "file")
            check_server && test_invoice_file "$2"
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [quick|full|performance|setup|all|file <path>|help]"
            echo ""
            echo "Options:"
            echo "  quick       - Run quick health checks"
            echo "  full        - Run full test suite"
            echo "  performance - Run performance tests"
            echo "  setup       - Setup test environment"
            echo "  all         - Run all tests"
            echo "  file <path> - Test specific invoice file"
            echo "  help        - Show this help"
            echo ""
            echo "Environment variables:"
            echo "  BASE_URL    - API base URL (default: http://localhost:8000)"
            echo "  PYTHON_CMD  - Python command (default: python)"
            ;;
        "")
            # Interactive mode
            if ! check_server; then
                exit 1
            fi

            while true; do
                show_menu
                read -p "Select option: " choice
                case $choice in
                    1) run_quick_test ;;
                    2) run_full_tests ;;
                    3) run_performance_tests ;;
                    4)
                        read -p "Enter path to invoice file: " file_path
                        test_invoice_file "$file_path"
                        ;;
                    5)
                        install_dependencies
                        setup_test_files
                        ;;
                    6)
                        install_dependencies
                        setup_test_files
                        run_full_tests
                        run_performance_tests
                        ;;
                    q|Q) break ;;
                    *) print_status "Invalid option" "ERROR" ;;
                esac
                echo ""
                read -p "Press Enter to continue..."
            done
            ;;
        *)
            print_status "Unknown option: $1" "ERROR"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"