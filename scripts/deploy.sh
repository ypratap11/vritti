#!/bin/bash
# scripts/deploy.sh - Comprehensive deployment automation script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_NAME="vritti-invoice-ai"
DEPLOY_USER=${DEPLOY_USER:-"vritti"}
DEPLOY_HOST=${DEPLOY_HOST:-"your-server.com"}
DEPLOY_PORT=${DEPLOY_PORT:-"22"}
DEPLOY_PATH=${DEPLOY_PATH:-"/opt/vritti"}
BACKUP_PATH=${BACKUP_PATH:-"/opt/vritti/backups"}
PYTHON_VERSION=${PYTHON_VERSION:-"3.9"}
SERVICE_NAME="vritti-ai"

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# Pre-deployment checks
pre_deploy_checks() {
    log "Running pre-deployment checks..."

    # Check if we're on the correct branch
    CURRENT_BRANCH=$(git branch --show-current)
    if [[ "$CURRENT_BRANCH" != "main" && "$CURRENT_BRANCH" != "master" ]]; then
        warning "You're not on main/master branch. Current: $CURRENT_BRANCH"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "Deployment cancelled"
        fi
    fi

    # Check if working directory is clean
    if [[ -n $(git status --porcelain) ]]; then
        error "Working directory is not clean. Please commit or stash changes."
    fi

    # Check if requirements.txt exists
    if [[ ! -f "requirements.txt" ]]; then
        error "requirements.txt not found"
    fi

    # Run tests
    log "Running tests before deployment..."
    if ! ./run_tests.sh quick; then
        error "Tests failed. Deployment cancelled."
    fi

    success "Pre-deployment checks passed"
}

# Create backup
create_backup() {
    log "Creating backup of current deployment..."

    BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S)"

    ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "
        if [ -d '$DEPLOY_PATH' ]; then
            mkdir -p $BACKUP_PATH
            cp -r $DEPLOY_PATH $BACKUP_PATH/$BACKUP_NAME
            echo 'Backup created: $BACKUP_PATH/$BACKUP_NAME'
        fi
    "

    success "Backup created: $BACKUP_NAME"
}

# Deploy application
deploy_app() {
    log "Deploying application to $DEPLOY_HOST..."

    # Create deployment package
    TEMP_DIR=$(mktemp -d)
    PACKAGE_NAME="$PROJECT_NAME-$(date +%Y%m%d-%H%M%S).tar.gz"

    log "Creating deployment package..."
    tar -czf "$TEMP_DIR/$PACKAGE_NAME" \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='tests' \
        --exclude='logs' \
        --exclude='.env' \
        --exclude='uploads' \
        .

    # Upload package
    log "Uploading package to server..."
    scp -P $DEPLOY_PORT "$TEMP_DIR/$PACKAGE_NAME" $DEPLOY_USER@$DEPLOY_HOST:/tmp/

    # Deploy on server
    ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "
        set -e

        # Stop the service
        sudo systemctl stop $SERVICE_NAME || true

        # Create deployment directory
        sudo mkdir -p $DEPLOY_PATH
        sudo chown $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH

        # Extract package
        cd $DEPLOY_PATH
        rm -rf src/ config/ scripts/ requirements.txt || true
        tar -xzf /tmp/$PACKAGE_NAME

        # Setup virtual environment
        if [ ! -d 'venv' ]; then
            python$PYTHON_VERSION -m venv venv
        fi

        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt

        # Create necessary directories
        mkdir -p logs uploads data/models

        # Set permissions
        sudo chown -R $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH
        chmod +x scripts/*.sh

        # Start the service
        sudo systemctl start $SERVICE_NAME
        sudo systemctl enable $SERVICE_NAME

        # Cleanup
        rm /tmp/$PACKAGE_NAME
    "

    # Cleanup local temp files
    rm -rf "$TEMP_DIR"

    success "Application deployed successfully"
}

# Health check
health_check() {
    log "Performing health check..."

    # Wait for service to start
    sleep 10

    # Check if service is running
    ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "
        if sudo systemctl is-active --quiet $SERVICE_NAME; then
            echo 'Service is running'
        else
            echo 'Service is not running'
            sudo systemctl status $SERVICE_NAME
            exit 1
        fi
    "

    # Check HTTP endpoint
    for i in {1..5}; do
        if curl -f "http://$DEPLOY_HOST:8000/" > /dev/null 2>&1; then
            success "Health check passed"
            return 0
        fi
        log "Health check attempt $i/5 failed, retrying..."
        sleep 5
    done

    error "Health check failed after 5 attempts"
}

# Rollback function
rollback() {
    log "Rolling back to previous version..."

    # Get latest backup
    LATEST_BACKUP=$(ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "ls -t $BACKUP_PATH | head -n 1")

    if [[ -z "$LATEST_BACKUP" ]]; then
        error "No backup found for rollback"
    fi

    ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "
        set -e

        # Stop service
        sudo systemctl stop $SERVICE_NAME

        # Restore backup
        rm -rf $DEPLOY_PATH
        cp -r $BACKUP_PATH/$LATEST_BACKUP $DEPLOY_PATH

        # Start service
        sudo systemctl start $SERVICE_NAME
    "

    success "Rollback completed: $LATEST_BACKUP"
}

# Database migration (if needed)
migrate_database() {
    log "Running database migrations..."

    ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "
        cd $DEPLOY_PATH
        source venv/bin/activate

        # Add your database migration commands here
        # python manage.py migrate
        # alembic upgrade head

        echo 'Database migrations completed'
    "

    success "Database migrations completed"
}

# Update configuration
update_config() {
    log "Updating configuration..."

    # Copy environment-specific config
    scp -P $DEPLOY_PORT config/production.env $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PATH/.env

    # Update systemd service file if needed
    if [[ -f "config/$SERVICE_NAME.service" ]]; then
        scp -P $DEPLOY_PORT "config/$SERVICE_NAME.service" $DEPLOY_USER@$DEPLOY_HOST:/tmp/
        ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "
            sudo mv /tmp/$SERVICE_NAME.service /etc/systemd/system/
            sudo systemctl daemon-reload
        "
    fi

    success "Configuration updated"
}

# Cleanup old backups
cleanup_backups() {
    log "Cleaning up old backups..."

    ssh -p $DEPLOY_PORT $DEPLOY_USER@$DEPLOY_HOST "
        # Keep only last 5 backups
        cd $BACKUP_PATH
        ls -t | tail -n +6 | xargs -r rm -rf
        echo 'Cleanup completed'
    "

    success "Old backups cleaned up"
}

# Send deployment notification
send_notification() {
    local status=$1
    local message=$2

    # Slack notification (if webhook URL is set)
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚀 Vritti AI Deployment: $status - $message\"}" \
            "$SLACK_WEBHOOK_URL"
    fi

    # Email notification (if configured)
    if [[ -n "$NOTIFICATION_EMAIL" ]]; then
        echo "$message" | mail -s "Vritti AI Deployment: $status" "$NOTIFICATION_EMAIL"
    fi

    log "Notification sent: $status"
}

# Main deployment function
main_deploy() {
    log "Starting deployment of Vritti Invoice AI..."

    case "${1:-deploy}" in
        "deploy")
            pre_deploy_checks
            create_backup
            deploy_app
            update_config
            migrate_database
            health_check
            cleanup_backups
            send_notification "SUCCESS" "Deployment completed successfully"
            success "Deployment completed successfully! 🎉"
            ;;
        "rollback")
            rollback
            health_check
            send_notification "ROLLBACK" "Rollback completed"
            success "Rollback completed successfully!"
            ;;
        "health")
            health_check
            ;;
        "backup")
            create_backup
            ;;
        *)
            echo "Usage: $0 [deploy|rollback|health|backup]"
            echo ""
            echo "Commands:"
            echo "  deploy   - Full deployment (default)"
            echo "  rollback - Rollback to previous version"
            echo "  health   - Health check only"
            echo "  backup   - Create backup only"
            exit 1
            ;;
    esac
}

# Trap errors and send notification
trap 'send_notification "FAILED" "Deployment failed"; error "Deployment failed"' ERR

# Run main function
main_deploy "$@"

---

# scripts/setup-server.sh - Initial server setup script
#!/bin/bash

set -e

log() {
    echo -e "\033[0;34m[$(date +'%Y-%m-%d %H:%M:%S')] $1\033[0m"
}

success() {
    echo -e "\033[0;32m✅ $1\033[0m"
}

error() {
    echo -e "\033[0;31m❌ $1\033[0m"
    exit 1
}

log "Setting up Vritti Invoice AI server..."

# Update system
log "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
log "Installing required packages..."
sudo apt install -y \
    python3.9 \
    python3.9-venv \
    python3.9-dev \
    python3-pip \
    nginx \
    redis-server \
    postgresql \
    postgresql-contrib \
    git \
    curl \
    htop \
    supervisor \
    certbot \
    python3-certbot-nginx \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    tesseract-ocr-spa \
    imagemagick \
    poppler-utils

# Create vritti user
log "Creating vritti user..."
if ! id "vritti" &>/dev/null; then
    sudo useradd -m -s /bin/bash vritti
    sudo usermod -aG sudo vritti
fi

# Setup directories
log "Setting up directories..."
sudo mkdir -p /opt/vritti/{logs,uploads,data/models,backups}
sudo chown -R vritti:vritti /opt/vritti

# Setup PostgreSQL
log "Setting up PostgreSQL..."
sudo -u postgres createuser vritti || true
sudo -u postgres createdb vritti_ai || true
sudo -u postgres psql -c "ALTER USER vritti PASSWORD 'your_secure_password';" || true

# Setup Redis
log "Configuring Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Install Python dependencies globally needed
log "Installing global Python packages..."
pip3 install --upgrade pip setuptools wheel

# Setup systemd service
log "Creating systemd service..."
cat > /tmp/vritti-ai.service << 'EOF'
[Unit]
Description=Vritti Invoice AI Service
After=network.target

[Service]
Type=simple
User=vritti
Group=vritti
WorkingDirectory=/opt/vritti
Environment=PATH=/opt/vritti/venv/bin
ExecStart=/opt/vritti/venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/vritti-ai.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vritti-ai

# Setup Nginx
log "Configuring Nginx..."
cat > /tmp/vritti-nginx.conf << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static/ {
        alias /opt/vritti/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /uploads/ {
        alias /opt/vritti/uploads/;
        expires 1d;
    }
}
EOF

sudo mv /tmp/vritti-nginx.conf /etc/nginx/sites-available/vritti-ai
sudo ln -sf /etc/nginx/sites-available/vritti-ai /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

# Setup SSL (optional)
log "SSL setup..."
echo "To setup SSL, run: sudo certbot --nginx -d your-domain.com"

# Setup log rotation
log "Setting up log rotation..."
cat > /tmp/vritti-logrotate << 'EOF'
/opt/vritti/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 vritti vritti
    postrotate
        systemctl reload vritti-ai
    endscript
}
EOF

sudo mv /tmp/vritti-logrotate /etc/logrotate.d/vritti-ai

# Setup monitoring script
log "Setting up monitoring..."
cat > /opt/vritti/monitor.sh << 'EOF'
#!/bin/bash
# Basic monitoring script

LOGFILE="/opt/vritti/logs/monitor.log"
WEBHOOK_URL="${SLACK_WEBHOOK_URL}"

check_service() {
    if ! systemctl is-active --quiet vritti-ai; then
        echo "$(date): Service is down" >> $LOGFILE
        if [[ -n "$WEBHOOK_URL" ]]; then
            curl -X POST -H 'Content-type: application/json' \
                --data '{"text":"🚨 Vritti AI service is down!"}' \
                "$WEBHOOK_URL"
        fi
        systemctl restart vritti-ai
    fi
}

check_disk_space() {
    USAGE=$(df /opt/vritti | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $USAGE -gt 80 ]; then
        echo "$(date): Disk usage high: $USAGE%" >> $LOGFILE
        if [[ -n "$WEBHOOK_URL" ]]; then
            curl -X POST -H 'Content-type: application/json' \
                --data "{\"text\":\"⚠️ Vritti AI disk usage high: $USAGE%\"}" \
                "$WEBHOOK_URL"
        fi
    fi
}

check_memory() {
    MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ $MEM_USAGE -gt 85 ]; then
        echo "$(date): Memory usage high: $MEM_USAGE%" >> $LOGFILE
    fi
}

check_service
check_disk_space
check_memory
EOF

chmod +x /opt/vritti/monitor.sh
chown vritti:vritti /opt/vritti/monitor.sh

# Setup cron job for monitoring
log "Setting up monitoring cron job..."
echo "*/5 * * * * /opt/vritti/monitor.sh" | sudo -u vritti crontab -

# Setup firewall
log "Configuring firewall..."
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Final instructions
success "Server setup completed!"
echo ""
echo "Next steps:"
echo "1. Update /etc/nginx/sites-available/vritti-ai with your domain"
echo "2. Setup SSL: sudo certbot --nginx -d your-domain.com"
echo "3. Configure environment variables in /opt/vritti/.env"
echo "4. Deploy application: ./scripts/deploy.sh"
echo "5. Setup Google Cloud credentials"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status vritti-ai     # Check service status"
echo "  sudo journalctl -u vritti-ai -f     # View logs"
echo "  sudo nginx -t                       # Test nginx config"
echo "  sudo systemctl reload nginx         # Reload nginx"

---

# scripts/docker-deploy.sh - Docker-based deployment
#!/bin/bash

set -e

# Configuration
REGISTRY="ghcr.io"
IMAGE_NAME="your-username/vritti-invoice-ai"
CONTAINER_NAME="vritti-ai"
NETWORK_NAME="vritti-network"
VOLUME_NAME="vritti-data"

log() {
    echo -e "\033[0;34m[$(date +'%Y-%m-%d %H:%M:%S')] $1\033[0m"
}

success() {
    echo -e "\033[0;32m✅ $1\033[0m"
}

# Build and push image
build_and_push() {
    log "Building Docker image..."

    docker build -t $IMAGE_NAME:latest .
    docker tag $IMAGE_NAME:latest $REGISTRY/$IMAGE_NAME:latest

    log "Pushing to registry..."
    docker push $REGISTRY/$IMAGE_NAME:latest

    success "Image built and pushed"
}

# Deploy with Docker Compose
deploy_compose() {
    log "Deploying with Docker Compose..."

    cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  vritti-ai:
    image: ghcr.io/your-username/vritti-invoice-ai:latest
    container_name: vritti-ai
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/vritti_ai
      - REDIS_URL=redis://redis:6379
    volumes:
      - vritti-uploads:/app/uploads
      - vritti-logs:/app/logs
      - ./credentials:/app/credentials:ro
    depends_on:
      - postgres
      - redis
    networks:
      - vritti-network

  postgres:
    image: postgres:14-alpine
    container_name: vritti-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=vritti_ai
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - vritti-network

  redis:
    image: redis:6-alpine
    container_name: vritti-redis
    restart: unless-stopped
    networks:
      - vritti-network

  nginx:
    image: nginx:alpine
    container_name: vritti-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - vritti-ai
    networks:
      - vritti-network

volumes:
  vritti-uploads:
  vritti-logs:
  postgres-data:

networks:
  vritti-network:
    driver: bridge
EOF

    docker-compose -f docker-compose.prod.yml up -d

    success "Docker deployment completed"
}

# Main function
case "${1:-compose}" in
    "build")
        build_and_push
        ;;
    "compose")
        deploy_compose
        ;;
    "both")
        build_and_push
        deploy_compose
        ;;
    *)
        echo "Usage: $0 [build|compose|both]"
        exit 1
        ;;
esac