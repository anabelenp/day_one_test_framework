#!/bin/bash

# Performance Test Runner for Day-1 Framework
# Executes comprehensive performance testing using JMeter and Locust

set -e

# Configuration
HOST=${HOST:-"http://localhost:8080"}
RESULTS_DIR=${RESULTS_DIR:-"reports/performance"}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create results directory
mkdir -p $RESULTS_DIR

echo -e "${BLUE}🚀 Starting Performance Test Suite - $TIMESTAMP${NC}"
echo -e "${BLUE}Target Host: $HOST${NC}"
echo -e "${BLUE}Results Directory: $RESULTS_DIR${NC}"
echo ""

# Function to check if service is available
check_service() {
    echo -e "${YELLOW}🔍 Checking service availability...${NC}"
    if curl -s --max-time 10 "$HOST/api/v2/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Service is available${NC}"
        return 0
    else
        echo -e "${RED}❌ Service is not available at $HOST${NC}"
        echo -e "${YELLOW}💡 Make sure to start the local environment:${NC}"
        echo -e "   docker-compose -f docker-compose.local.yml up -d"
        return 1
    fi
}

# Function to run Locust test
run_locust_test() {
    local test_name=$1
    local users=$2
    local spawn_rate=$3
    local run_time=$4
    local description=$5
    
    echo -e "${BLUE}📊 Running Locust $test_name Test...${NC}"
    echo -e "${YELLOW}   Users: $users, Spawn Rate: $spawn_rate/s, Duration: $run_time${NC}"
    echo -e "${YELLOW}   Description: $description${NC}"
    
    locust -f tests/performance/locust/netskope_load_test.py \
           --host=$HOST \
           --users=$users \
           --spawn-rate=$spawn_rate \
           --run-time=$run_time \
           --headless \
           --csv=$RESULTS_DIR/locust_${test_name}_$TIMESTAMP \
           --logfile=$RESULTS_DIR/locust_${test_name}_$TIMESTAMP.log \
           --loglevel=INFO
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Locust $test_name test completed successfully${NC}"
    else
        echo -e "${RED}❌ Locust $test_name test failed${NC}"
        return 1
    fi
}

# Function to run JMeter test
run_jmeter_test() {
    local test_name=$1
    local users=$2
    local ramp_time=$3
    local duration=$4
    local description=$5
    
    echo -e "${BLUE}🔧 Running JMeter $test_name Test...${NC}"
    echo -e "${YELLOW}   Users: $users, Ramp Time: ${ramp_time}s, Duration: ${duration}s${NC}"
    echo -e "${YELLOW}   Description: $description${NC}"
    
    # Check if JMeter is installed
    if ! command -v jmeter &> /dev/null; then
        echo -e "${YELLOW}⚠️  JMeter not found. Installing via Homebrew...${NC}"
        if command -v brew &> /dev/null; then
            brew install jmeter
        else
            echo -e "${RED}❌ Homebrew not found. Please install JMeter manually${NC}"
            return 1
        fi
    fi
    
    jmeter -n -t tests/performance/jmeter/netskope_api_load_test.jmx \
           -Jbase_url=$HOST \
           -Jusers=$users \
           -Jramp_time=$ramp_time \
           -Jduration=$duration \
           -l $RESULTS_DIR/jmeter_${test_name}_$TIMESTAMP.jtl \
           -e -o $RESULTS_DIR/jmeter_${test_name}_report_$TIMESTAMP \
           -j $RESULTS_DIR/jmeter_${test_name}_$TIMESTAMP.log
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ JMeter $test_name test completed successfully${NC}"
        echo -e "${BLUE}📊 JMeter HTML report: $RESULTS_DIR/jmeter_${test_name}_report_$TIMESTAMP/index.html${NC}"
    else
        echo -e "${RED}❌ JMeter $test_name test failed${NC}"
        return 1
    fi
}

# Function to run Python load test
run_python_test() {
    echo -e "${BLUE}🐍 Running Python Load Test...${NC}"
    echo -e "${YELLOW}   Description: ThreadPoolExecutor-based concurrent testing${NC}"
    
    pytest tests/performance/test_load.py -v --tb=short
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Python load test completed successfully${NC}"
    else
        echo -e "${RED}❌ Python load test failed${NC}"
        return 1
    fi
}

# Function to analyze results
analyze_results() {
    echo -e "${BLUE}📈 Analyzing Performance Results...${NC}"
    
    # Check if analysis script exists
    if [ -f "scripts/analyze_performance_results.py" ]; then
        # Find the most recent Locust results file
        latest_locust_file=$(find $RESULTS_DIR -name "locust_*_${TIMESTAMP}_stats.csv" | head -1)
        
        if [ -n "$latest_locust_file" ]; then
            echo -e "${YELLOW}📊 Analyzing: $latest_locust_file${NC}"
            python scripts/analyze_performance_results.py "$latest_locust_file" --output-dir "$RESULTS_DIR"
        else
            echo -e "${YELLOW}⚠️  No Locust results found for analysis${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Performance analysis script not found${NC}"
    fi
}

# Function to generate summary report
generate_summary() {
    echo -e "${BLUE}📋 Generating Performance Summary...${NC}"
    
    cat > $RESULTS_DIR/performance_summary_$TIMESTAMP.md << EOF
# Performance Test Summary - $TIMESTAMP

## Test Configuration
- **Target Host**: $HOST
- **Test Date**: $(date)
- **Results Directory**: $RESULTS_DIR

## Tests Executed

### Locust Tests
EOF

    # Add Locust test results if they exist
    for file in $RESULTS_DIR/locust_*_${TIMESTAMP}_stats.csv; do
        if [ -f "$file" ]; then
            test_name=$(basename "$file" | sed "s/locust_\(.*\)_${TIMESTAMP}_stats.csv/\1/")
            echo "- **$test_name Test**: $(basename "$file")" >> $RESULTS_DIR/performance_summary_$TIMESTAMP.md
        fi
    done

    cat >> $RESULTS_DIR/performance_summary_$TIMESTAMP.md << EOF

### JMeter Tests
EOF

    # Add JMeter test results if they exist
    for file in $RESULTS_DIR/jmeter_*_${TIMESTAMP}.jtl; do
        if [ -f "$file" ]; then
            test_name=$(basename "$file" | sed "s/jmeter_\(.*\)_${TIMESTAMP}.jtl/\1/")
            echo "- **$test_name Test**: $(basename "$file")" >> $RESULTS_DIR/performance_summary_$TIMESTAMP.md
        fi
    done

    cat >> $RESULTS_DIR/performance_summary_$TIMESTAMP.md << EOF

## Results Files
- **Summary Report**: performance_summary_$TIMESTAMP.md
- **Analysis Results**: performance_analysis.json (if available)
- **Performance Charts**: performance_charts.png (if available)

## Next Steps
1. Review individual test results in the results directory
2. Compare against performance baselines and SLAs
3. Investigate any performance issues or failures
4. Update performance benchmarks if needed

## Monitoring Links
- **Grafana**: http://localhost:3000 (admin/netskope_grafana_2024)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686

EOF

    echo -e "${GREEN}✅ Performance summary generated: $RESULTS_DIR/performance_summary_$TIMESTAMP.md${NC}"
}

# Main execution flow
main() {
    # Check service availability
    if ! check_service; then
        exit 1
    fi
    
    echo ""
    
    # 1. Smoke Test (Quick validation)
    echo -e "${BLUE}==================== SMOKE TEST ====================${NC}"
    run_locust_test "smoke" 5 1 "60s" "Quick validation that system handles basic load"
    echo ""
    
    # 2. Load Test (Normal usage)
    echo -e "${BLUE}==================== LOAD TEST ====================${NC}"
    run_locust_test "load" 50 5 "300s" "Normal business hours simulation"
    echo ""
    
    # 3. Python Load Test
    echo -e "${BLUE}================== PYTHON LOAD TEST ================${NC}"
    run_python_test
    echo ""
    
    # 4. JMeter Load Test (Alternative tool validation)
    echo -e "${BLUE}================== JMETER LOAD TEST ================${NC}"
    run_jmeter_test "load" 50 60 300 "JMeter-based load testing validation"
    echo ""

        # 4b. JMeter DLP-specific Load Test
        echo -e "${BLUE}============= JMETER DLP LOAD TEST ===============${NC}"
        echo -e "${YELLOW}Running DLP-specific JMeter plan: tests/performance/jmeter/dlp_scan_load_test.jmx${NC}"
        jmeter -n -t tests/performance/jmeter/dlp_scan_load_test.jmx \
            -Jbase_url=$HOST -Jusers=50 -Jramp_time=60 -Jduration=300 \
            -l $RESULTS_DIR/dlp_jmeter_test_$TIMESTAMP.jtl \
            -e -o $RESULTS_DIR/dlp_jmeter_report_$TIMESTAMP \
            -j $RESULTS_DIR/dlp_jmeter_$TIMESTAMP.log
        echo ""
    
    # 5. Stress Test (High load) - Optional, can be skipped with --no-stress
    if [[ "$*" != *"--no-stress"* ]]; then
        echo -e "${BLUE}=================== STRESS TEST ===================${NC}"
        echo -e "${YELLOW}⚠️  Running stress test with high load (200 users)${NC}"
        echo -e "${YELLOW}   This may take 10+ minutes and consume significant resources${NC}"
        read -p "Continue with stress test? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_locust_test "stress" 200 10 "600s" "High load stress testing to find breaking points"
        else
            echo -e "${YELLOW}⏭️  Skipping stress test${NC}"
        fi
        echo ""
    fi
    
    # 6. Analyze Results
    echo -e "${BLUE}=================== ANALYSIS ======================${NC}"
    analyze_results
    echo ""
    
    # 7. Generate Summary Report
    echo -e "${BLUE}=================== SUMMARY ======================${NC}"
    generate_summary
    echo ""
    
    # Final summary
    echo -e "${GREEN}🎉 Performance Test Suite Completed Successfully!${NC}"
    echo -e "${BLUE}📊 Results available in: $RESULTS_DIR${NC}"
    echo -e "${BLUE}📋 Summary report: $RESULTS_DIR/performance_summary_$TIMESTAMP.md${NC}"
    echo ""
    echo -e "${YELLOW}📈 To view detailed results:${NC}"
    echo -e "   open $RESULTS_DIR/performance_summary_$TIMESTAMP.md"
    
    # Check for JMeter HTML reports
    jmeter_reports=$(find $RESULTS_DIR -name "jmeter_*_report_$TIMESTAMP" -type d 2>/dev/null)
    if [ -n "$jmeter_reports" ]; then
        for report_dir in $jmeter_reports; do
            echo -e "   open $report_dir/index.html"
        done
    fi
    
    echo ""
    echo -e "${YELLOW}🔍 To monitor system performance:${NC}"
    echo -e "   open http://localhost:3000    # Grafana"
    echo -e "   open http://localhost:9090    # Prometheus"
    echo -e "   open http://localhost:16686   # Jaeger"
}

# Help function
show_help() {
    echo "Performance Test Runner for Day-1 Framework"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --host HOST        Target host (default: http://localhost:8080)"
    echo "  --results-dir DIR  Results directory (default: reports/performance)"
    echo "  --no-stress        Skip stress testing"
    echo "  --help             Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  HOST               Target host URL"
    echo "  RESULTS_DIR        Results directory path"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run all tests with defaults"
    echo "  $0 --no-stress                       # Skip stress testing"
    echo "  $0 --host http://staging.example.com # Test against staging"
    echo "  HOST=http://localhost:8080 $0        # Use environment variable"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --results-dir)
            RESULTS_DIR="$2"
            shift 2
            ;;
        --no-stress)
            # This is handled in the main function
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function with all arguments
main "$@"