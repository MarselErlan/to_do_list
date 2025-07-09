# Production Database Setup Guide for TaskFlow AI

## 🎯 **Recommended: PostgreSQL for Production**

Your application is already configured for PostgreSQL with `psycopg2-binary` installed.

### **PostgreSQL Configuration**

#### **1. Local Development**

```bash
# Install PostgreSQL locally
brew install postgresql  # macOS
sudo apt-get install postgresql postgresql-contrib  # Ubuntu

# Start PostgreSQL service
brew services start postgresql  # macOS
sudo systemctl start postgresql  # Ubuntu

# Create database
createdb taskflow_dev
```

#### **2. Environment Configuration**

```env
# .env file for production
DATABASE_URL=postgresql://username:password@localhost:5432/taskflow_production

# Example formats:
DATABASE_URL=postgresql://taskflow_user:secure_password@localhost:5432/taskflow_db
DATABASE_URL=postgresql://user:pass@db.example.com:5432/taskflow

# For cloud providers:
DATABASE_URL=postgresql://user:pass@hostname:5432/dbname?sslmode=require
```

#### **3. Cloud PostgreSQL Providers**

##### **Railway (Recommended for this project)**

```env
# Railway provides DATABASE_URL automatically
DATABASE_URL=postgresql://postgres:password@roundhouse.proxy.rlwy.net:12345/railway
```

##### **Supabase**

```env
DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:5432/postgres
```

##### **Neon**

```env
DATABASE_URL=postgresql://username:password@ep-cool-darkness-123456.us-east-1.aws.neon.tech/neondb
```

##### **Heroku Postgres**

```env
DATABASE_URL=postgres://user:password@hostname:5432/database_name
```

##### **AWS RDS**

```env
DATABASE_URL=postgresql://username:password@taskflow-db.123456789012.us-east-1.rds.amazonaws.com:5432/taskflow
```

## 🔧 **Database Migration Setup**

Your application uses **Alembic** for database migrations:

### **1. Initialize Alembic (Already Done)**

```bash
# Your project already has alembic configured
ls alembic/versions/  # Shows existing migrations
```

### **2. Run Migrations**

```bash
# Apply all migrations to production database
alembic upgrade head

# Create new migration (when you change models)
alembic revision --autogenerate -m "Add new feature"
```

### **3. Production Migration Command**

```bash
# Set production DATABASE_URL and run migrations
export DATABASE_URL="postgresql://user:pass@host:5432/db"
alembic upgrade head
```

## 🚀 **Quick Fix for Current Issue**

### **Option 1: Fix SQLite for Development**

```bash
# Create proper .env file
echo 'DATABASE_URL=sqlite:///./taskflow.db' > .env
echo 'OPENAI_API_KEY=your-openai-key' >> .env
echo 'SECRET_KEY=your-secret-key-min-32-chars-long' >> .env
```

### **Option 2: Use PostgreSQL Immediately**

```bash
# Install and setup PostgreSQL
brew install postgresql
brew services start postgresql
createdb taskflow_dev

# Configure .env
echo 'DATABASE_URL=postgresql://localhost:5432/taskflow_dev' > .env
echo 'OPENAI_API_KEY=your-openai-key' >> .env
echo 'SECRET_KEY=your-secret-key-min-32-chars-long' >> .env

# Run migrations
alembic upgrade head
```

## 📊 **Database Comparison**

| Database       | Development  | Production   | Scalability | Complexity  |
| -------------- | ------------ | ------------ | ----------- | ----------- |
| **SQLite**     | ✅ Excellent | ❌ Poor      | ❌ Limited  | ✅ Simple   |
| **PostgreSQL** | ✅ Good      | ✅ Excellent | ✅ High     | 🟡 Moderate |
| **MySQL**      | ✅ Good      | ✅ Good      | ✅ High     | 🟡 Moderate |

## 🔐 **Production Security Best Practices**

### **1. Connection Security**

```env
# Always use SSL in production
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require

# Use connection pooling
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require&pool_size=20&max_overflow=30
```

### **2. Environment Variables**

```bash
# Never commit credentials to git
# Use environment-specific .env files

# Development
DATABASE_URL=postgresql://localhost:5432/taskflow_dev

# Production
DATABASE_URL=postgresql://prod_user:secure_pass@prod-db.com:5432/taskflow_prod
```

### **3. Database User Permissions**

```sql
-- Create dedicated application user
CREATE USER taskflow_app WITH PASSWORD 'secure_password';

-- Grant only necessary permissions
GRANT CONNECT ON DATABASE taskflow_production TO taskflow_app;
GRANT USAGE ON SCHEMA public TO taskflow_app;
GRANT CREATE ON SCHEMA public TO taskflow_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO taskflow_app;
```

## 🔄 **Backup and Recovery**

### **1. Automated Backups**

```bash
# Daily backup script
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore from backup
psql $DATABASE_URL < backup_20240109.sql
```

### **2. Cloud Provider Backups**

- **Railway**: Automatic daily backups
- **Supabase**: Automatic backups with point-in-time recovery
- **AWS RDS**: Automated backups with configurable retention

## 🎯 **Recommended Production Setup**

### **For TaskFlow AI, I recommend:**

1. **Database**: PostgreSQL on Railway or Supabase
2. **Environment**: Separate dev/staging/production databases
3. **Migrations**: Automated via CI/CD pipeline
4. **Backups**: Daily automated backups
5. **Monitoring**: Database performance monitoring

### **Complete Production .env Example**

```env
# Database
DATABASE_URL=postgresql://username:password@hostname:5432/taskflow_production

# API Keys
OPENAI_API_KEY=sk-your-actual-openai-key
LANGCHAIN_API_KEY=your-langchain-key

# Security
SECRET_KEY=your-super-secure-32-character-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email (SendGrid)
SENDGRID_API_KEY=your-sendgrid-key
MAIL_FROM=noreply@yourdomain.com

# Google Cloud (for voice assistant)
GOOGLE_CLOUD_CREDENTIALS_JSON={"type":"service_account",...}
GOOGLE_CLOUD_PROJECT=your-gcp-project-id

# Monitoring
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=TaskFlow-Production
```

## 🚀 **Immediate Next Steps**

1. **Choose database provider** (Railway/Supabase recommended)
2. **Create production database**
3. **Configure environment variables**
4. **Run database migrations**
5. **Test application startup**

Your application architecture is production-ready - you just need proper database configuration!
