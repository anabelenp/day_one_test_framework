pipeline {
    agent any
    
    environment {
        PYTHON_VERSION = '3.11'
        TESTING_MODE = 'local'
        DOCKER_COMPOSE_FILE = 'docker-compose.local.yml'
    }
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 60, unit: 'MINUTES')
        timestamps()
        ansiColor('xterm')
    }
    
    stages {
        stage('Checkout & Setup') {
            steps {
                echo '🔄 Setting up environment...'
                
                // Clean workspace
                cleanWs()
                
                // Checkout code
                checkout scm
                
                // Setup Python environment
                sh '''
                    python${PYTHON_VERSION} -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -e .
                    pip install pytest pytest-html pytest-cov pytest-xvfb docker-compose
                '''
                
                // Verify installation
                sh '''
                    . venv/bin/activate
                    python -c "from src.environment_manager import get_current_environment; print(f'✅ Environment: {get_current_environment().value}')"
                '''
            }
        }
        
        stage('Security Scans') {
            parallel {
                stage('SAST - Bandit') {
                    steps {
                        echo '🔒 Running Bandit security scan...'
                        sh '''
                            . venv/bin/activate
                            pip install bandit[toml]
                            mkdir -p reports
                            bandit -r src/ tests/ -f json -o reports/bandit-report.json || true
                            bandit -r src/ tests/ -f html -o reports/bandit-report.html || true
                            bandit -r src/ tests/ -ll -i
                        '''
                    }
                    post {
                        always {
                            publishHTML([
                                allowMissing: false,
                                alwaysLinkToLastBuild: true,
                                keepAll: true,
                                reportDir: 'reports',
                                reportFiles: 'bandit-report.html',
                                reportName: 'Bandit Security Report'
                            ])
                        }
                    }
                }
                
                stage('Dependency Scan') {
                    steps {
                        echo '📦 Running dependency security scan...'
                        sh '''
                            . venv/bin/activate
                            pip install safety pip-audit
                            mkdir -p reports
                            safety check --json --output reports/safety-report.json || true
                            safety check --full-report || true
                            pip-audit --desc --format json --output reports/pip-audit-report.json || true
                            pip-audit --desc || true
                        '''
                    }
                }
                
                stage('Secret Scan') {
                    steps {
                        echo '🔍 Running secret scan...'
                        sh '''
                            . venv/bin/activate
                            pip install truffleHog3
                            mkdir -p reports
                            trufflehog3 --format json --output reports/trufflehog-report.json . || true
                            trufflehog3 . || true
                        '''
                    }
                }
            }
        }
        
        stage('Unit Tests') {
            steps {
                echo '🧪 Running unit tests...'
                sh '''
                    . venv/bin/activate
                    mkdir -p reports
                    pytest tests/unit/ -v \
                        --cov=src \
                        --cov-report=xml \
                        --cov-report=html \
                        --html=reports/unit-test-report.html \
                        --self-contained-html \
                        --junitxml=reports/unit-test-results.xml
                '''
            }
            post {
                always {
                    publishTestResults testResultsPattern: 'reports/unit-test-results.xml'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports',
                        reportFiles: 'unit-test-report.html',
                        reportName: 'Unit Test Report'
                    ])
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'htmlcov',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                }
            }
        }
        
        stage('Integration Tests') {
            steps {
                echo '🔗 Running integration tests...'
                
                // Start local environment
                sh '''
                    docker-compose -f ${DOCKER_COMPOSE_FILE} up -d
                    
                    # Wait for services to be ready
                    echo "Waiting for services to start..."
                    sleep 30
                    
                    # Verify services are running
                    docker-compose -f ${DOCKER_COMPOSE_FILE} ps
                '''
                
                // Wait for services to be healthy
                sh '''
                    # Wait for Redis
                    timeout 60 bash -c 'until redis-cli -h localhost -p 6379 ping; do sleep 2; done'
                    
                    # Wait for Kafka (check if port is open)
                    timeout 60 bash -c 'until nc -z localhost 9092; do sleep 2; done'
                    
                    # Wait for MongoDB
                    timeout 60 bash -c 'until nc -z localhost 27017; do sleep 2; done'
                    
                    echo "All services are ready!"
                '''
                
                // Run integration tests
                sh '''
                    . venv/bin/activate
                    pytest tests/integration/ -v \
                        --html=reports/integration-test-report.html \
                        --self-contained-html \
                        --junitxml=reports/integration-test-results.xml \
                        -x
                '''
                
                // Run E2E tests
                sh '''
                    . venv/bin/activate
                    pytest tests/e2e/ -v \
                        --html=reports/e2e-test-report.html \
                        --self-contained-html \
                        --junitxml=reports/e2e-test-results.xml \
                        -x
                '''
            }
            post {
                always {
                    // Stop services
                    sh 'docker-compose -f ${DOCKER_COMPOSE_FILE} down -v || true'
                    
                    publishTestResults testResultsPattern: 'reports/*-test-results.xml'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports',
                        reportFiles: 'integration-test-report.html',
                        reportName: 'Integration Test Report'
                    ])
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports',
                        reportFiles: 'e2e-test-report.html',
                        reportName: 'E2E Test Report'
                    ])
                }
                failure {
                    // Collect service logs on failure
                    sh '''
                        echo "=== Docker Compose Services ==="
                        docker-compose -f ${DOCKER_COMPOSE_FILE} ps || true
                        
                        echo "=== Redis Logs ==="
                        docker-compose -f ${DOCKER_COMPOSE_FILE} logs redis || true
                        
                        echo "=== Kafka Logs ==="
                        docker-compose -f ${DOCKER_COMPOSE_FILE} logs kafka || true
                        
                        echo "=== MongoDB Logs ==="
                        docker-compose -f ${DOCKER_COMPOSE_FILE} logs mongodb || true
                    '''
                }
            }
        }

        stage('DLP Tests') {
            steps {
                echo '🗂️ Running DLP test suite (mock + integration)'

                // Run DLP tests in mock mode (fast)
                sh '''
                    . venv/bin/activate
                    mkdir -p reports
                    echo "Running DLP tests: mock mode"
                    TESTING_MODE=mock pytest tests/dlp/ -v --junitxml=reports/dlp-mock-results.xml || true
                '''

                // Run DLP tests against local stack if available
                sh '''
                    . venv/bin/activate
                    echo "Bringing up local stack for DLP integration checks"
                    docker-compose -f ${DOCKER_COMPOSE_FILE} up -d
                    # wait for basic services
                    sleep 15
                    TESTING_MODE=local pytest tests/dlp/ -v --junitxml=reports/dlp-integration-results.xml || true
                '''

                // Run DLP JMeter plan (if available)
                sh '''
                    . venv/bin/activate
                    mkdir -p reports
                    echo "Running DLP JMeter plan..."
                    if ! command -v jmeter &> /dev/null; then
                        echo "JMeter not found; attempting apt-get install jmeter (may require sudo)"
                        sudo apt-get update -y || true
                        sudo apt-get install -y jmeter || true
                    fi

                    jmeter -n -t tests/performance/jmeter/dlp_scan_load_test.jmx \
                           -Jbase_url=http://localhost:8080 -Jusers=20 -Jramp_time=30 -Jduration=60 \
                           -l reports/dlp-jmeter-results.jtl \
                           -e -o reports/dlp-jmeter-report || true
                '''
            }
            post {
                always {
                    // Collect results and publish
                    publishTestResults testResultsPattern: 'reports/dlp-*-results.xml'
                    publishHTML([
                        allowMissing: true,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports',
                        reportFiles: 'dlp-mock-results.xml',
                        reportName: 'DLP Mock Results'
                    ])
                    publishHTML([
                        allowMissing: true,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports/dlp-jmeter-report',
                        reportFiles: 'index.html',
                        reportName: 'DLP JMeter Report'
                    ])
                    publishHTML([
                        allowMissing: true,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports',
                        reportFiles: 'dlp-integration-results.xml',
                        reportName: 'DLP Integration Results'
                    ])
                }
                cleanup {
                    sh 'docker-compose -f ${DOCKER_COMPOSE_FILE} down -v || true'
                }
            }
        }
        
        stage('Performance Tests') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                echo '⚡ Running performance tests...'
                sh '''
                    . venv/bin/activate
                    pytest tests/performance/ -v \
                        --html=reports/performance-test-report.html \
                        --self-contained-html \
                        --junitxml=reports/performance-test-results.xml \
                        -m "not slow"
                '''
            }
            post {
                always {
                    publishTestResults testResultsPattern: 'reports/performance-test-results.xml'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports',
                        reportFiles: 'performance-test-report.html',
                        reportName: 'Performance Test Report'
                    ])
                }
            }
        }
        
        stage('Build Artifacts') {
            steps {
                echo '📦 Building deployment artifacts...'
                sh '''
                    . venv/bin/activate
                    
                    # Create distribution package
                    python setup.py sdist bdist_wheel
                    
                    # Build Docker images
                    docker build -f Dockerfile.test-runner -t netskope-sdet:${BUILD_NUMBER} .
                    docker build -f Dockerfile.integration -t netskope-sdet:integration-${BUILD_NUMBER} .
                    
                    # Tag latest for main branch
                    if [ "${BRANCH_NAME}" = "main" ]; then
                        docker tag netskope-sdet:${BUILD_NUMBER} netskope-sdet:latest
                        docker tag netskope-sdet:integration-${BUILD_NUMBER} netskope-sdet:integration-latest
                    fi
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'dist/*', fingerprint: true
                }
            }
        }
        
        stage('Deploy to Integration') {
            when {
                branch 'main'
            }
            steps {
                echo '🚀 Deploying to Integration Environment...'
                
                script {
                    def deploymentApproved = true
                    
                    // Request approval for deployment
                    try {
                        timeout(time: 5, unit: 'MINUTES') {
                            deploymentApproved = input(
                                message: 'Deploy to Integration Environment?',
                                ok: 'Deploy',
                                parameters: [
                                    booleanParam(defaultValue: true, description: 'Proceed with deployment?', name: 'DEPLOY')
                                ]
                            )
                        }
                    } catch (err) {
                        deploymentApproved = false
                        echo "Deployment approval timeout or cancelled"
                    }
                    
                    if (deploymentApproved) {
                        sh '''
                            . venv/bin/activate
                            
                            # Deploy to integration environment
                            python scripts/deploy_integration.py --namespace netskope-integration --wait
                            
                            # Run smoke tests
                            python -c "
                            import sys
                            sys.path.insert(0, 'src')
                            from environment_manager import EnvironmentManager
                            from service_manager import ServiceManager
                            
                            # Set environment to integration
                            env_manager = EnvironmentManager()
                            env_manager.set_environment_override('integration')
                            
                            # Test service connectivity
                            service_manager = ServiceManager()
                            health = service_manager.health_check_all()
                            
                            print(f'Integration environment health: {health}')
                            
                            if not all(health.values()):
                                print('❌ Some services are unhealthy')
                                sys.exit(1)
                            else:
                                print('✅ All services healthy')
                            "
                        '''
                    } else {
                        echo "Deployment skipped"
                    }
                }
            }
        }
        
        stage('Deploy to Staging') {
            when {
                tag pattern: "v\\d+\\.\\d+\\.\\d+", comparator: "REGEXP"
            }
            steps {
                echo '🏭 Deploying to Staging Environment...'
                
                script {
                    def deploymentApproved = input(
                        message: 'Deploy to Staging Environment (Production-like)?',
                        ok: 'Deploy',
                        parameters: [
                            booleanParam(defaultValue: false, description: 'This is a production-like environment. Proceed?', name: 'DEPLOY')
                        ]
                    )
                    
                    if (deploymentApproved) {
                        sh '''
                            . venv/bin/activate
                            
                            # Deploy to staging environment
                            python scripts/deploy_staging.py --namespace netskope-staging --wait
                            
                            # Run staging validation tests
                            pytest tests/staging/ -v --tb=short -x
                        '''
                    } else {
                        echo "Staging deployment cancelled"
                    }
                }
            }
        }
    }
    
    post {
        always {
            echo '🧹 Cleaning up...'
            
            // Archive all reports
            archiveArtifacts artifacts: 'reports/**/*', allowEmptyArchive: true
            
            // Clean up Docker resources
            sh '''
                docker system prune -f || true
                docker-compose -f ${DOCKER_COMPOSE_FILE} down -v || true
            '''
            
            // Clean workspace
            cleanWs()
        }
        
        success {
            echo '✅ Pipeline completed successfully!'
            
            // Notify success
            script {
                if (env.BRANCH_NAME == 'main') {
                    // Send notification for main branch success
                    echo "Main branch build successful - Integration deployment completed"
                }
            }
        }
        
        failure {
            echo '❌ Pipeline failed!'
            
            // Notify failure
            script {
                // Send notification for failure
                echo "Build failed for branch: ${env.BRANCH_NAME}"
            }
        }
        
        unstable {
            echo '⚠️ Pipeline completed with warnings!'
        }
    }
}
