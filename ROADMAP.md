# Classical Guitar Music Database - Project Roadmap

---

## Project Overview

A public, searchable classical guitar database built to preserve and share classical guitar repertoire. The platform aggregates data from Sheerpluck and IMSLP, provides clean search capabilities, and allows staff curation through an admin portal.

### Tech Stack

- **Frontend**: TypeScript + React (GitHub Pages)
- **Backend**: Python + Django + Django REST Framework
- **Database**: MySQL
- **Admin**: Django Admin with custom permissions
- **Hosting**: AWS Lightsail (Django + MySQL) behind Nginx + HTTPS

---

## Phase 1: Planning & Setup

### 1.1 Project Initialization
- [ ] Set up Git repository structure (monorepo or separate repos)
- [ ] Define project directory structure
- [ ] Create `.gitignore` for Python and Node.js
- [ ] Set up development environment documentation

### 1.2 Database Schema Design
- [x] Analyze Sheerpluck and IMSLP data structures
- [x] Design normalized MySQL schema (composers, works, arrangements, editions, etc.)
- [x] Define relationships and indexes
- [ ] Create ER diagram
- [x] Plan data normalization rules (name variants, dates, etc.)

### 1.3 API Design
- [x] Define RESTful endpoints
- [x] Plan filtering/search parameters
- [x] Design pagination strategy
- [x] Document API response formats
- [x] Plan versioning strategy

---

## Phase 2: Data Acquisition & Analysis ✅ COMPLETED

### 2.1 Data Collection
- [x] Research Sheerpluck data export options
- [~] Research IMSLP data access (API vs scraping) - **SKIPPED FOR NOW**
- [x] Identify legal/licensing considerations
- [x] Download sample datasets (Sheerpluck)
- [x] Document data source characteristics

### 2.2 Data Profiling
- [x] Analyze CSV structures from Sheerpluck
- [x] Identify inconsistencies and quality issues
- [x] Document field mappings to target schema
- [x] Create data dictionary
- [x] Identify duplicate detection strategies

### 2.3 ETL Pipeline Design
- [x] Design data cleaning rules
- [x] Plan field normalization (composer names, titles, dates)
- [x] Design deduplication logic
- [x] Plan incremental update strategy
- [x] Document transformation workflows

**Note**: Sheerpluck data successfully scraped and available in `sheerpluck_data.csv`. IMSLP integration deferred to future phase.

---

## Phase 3: Backend Development 🚧 IN PROGRESS

### 3.1 Django Project Setup ✅ COMPLETED
- [x] Initialize Django project
- [x] Configure MySQL connection
- [x] Set up virtual environment
- [x] Install core dependencies (DRF, MySQL connector, etc.)
- [x] Configure settings for dev/staging/prod
- [x] Set up environment variables management

### 3.2 Database Models ✅ COMPLETED
- [x] Create Django models matching schema design
- [x] Implement model relationships (ForeignKey, ManyToMany)
- [x] Add model validations
- [x] Create initial migrations
- [x] Implement model `__str__` methods for admin
- [x] Add indexes for search performance

### 3.3 Data Import Pipeline
- [ ] Build CSV parser for Sheerpluck data
- [ ] Build parser for IMSLP data (CSV or API)
- [ ] Implement data cleaning utilities
- [ ] Create Django management commands for import
- [ ] Implement deduplication logic
- [ ] Add progress logging and error handling
- [ ] Test with sample datasets

### 3.4 REST API
- [ ] Create serializers for all models
- [ ] Implement viewsets and endpoints
- [ ] Add filtering (django-filter)
- [ ] Implement full-text search (MySQL or separate engine)
- [ ] Add pagination
- [ ] Implement CORS for GitHub Pages
- [ ] Create API documentation (drf-spectacular/Swagger)
- [ ] Add rate limiting

### 3.5 Django Admin Portal
- [ ] Customize Django Admin for each model
- [ ] Add inline editing for related records
- [ ] Implement custom list filters
- [ ] Add search fields
- [ ] Create bulk actions (approve, merge, delete)
- [ ] Set up user permissions and groups
- [ ] Add audit logging for admin changes
- [ ] Create custom admin views for data quality reports

### 3.6 Testing
- [ ] Write unit tests for models
- [ ] Write tests for API endpoints
- [ ] Test data import pipeline
- [ ] Test admin portal functionality
- [ ] Load testing for API performance

---

## Phase 4: Frontend Development

### 4.1 React Project Setup
- [ ] Initialize React app with TypeScript (Vite or Create React App)
- [ ] Configure GitHub Pages deployment
- [ ] Set up routing (React Router)
- [ ] Configure API client (Axios/Fetch)
- [ ] Set up state management (Context API or Redux)
- [ ] Configure linting and formatting (ESLint, Prettier)

### 4.2 Core Components
- [ ] Header/Navigation
- [ ] Search bar with autocomplete
- [ ] Composer list/grid view
- [ ] Composer detail page
- [ ] Work detail page
- [ ] Advanced search/filter panel
- [ ] Results list with pagination
- [ ] Loading states and error handling

### 4.3 UI/UX Implementation
- [ ] Choose and implement UI library (Material-UI, Ant Design, or custom)
- [ ] Implement responsive design
- [ ] Add mobile navigation
- [ ] Create consistent typography and spacing
- [ ] Implement accessibility features (ARIA labels, keyboard navigation)
- [ ] Add favorites/bookmarks (local storage)

### 4.4 Features
- [ ] Full-text search functionality
- [ ] Advanced filtering (by period, difficulty, instrumentation)
- [ ] Sort options (name, date, popularity)
- [ ] Pagination controls
- [ ] External links to IMSLP, recordings, etc.
- [ ] Share functionality (copy link, social)

### 4.5 Testing
- [ ] Unit tests for utilities and helpers
- [ ] Component tests (React Testing Library)
- [ ] Integration tests for key user flows
- [ ] Cross-browser testing
- [ ] Mobile device testing

---

## Phase 5: DevOps & Deployment

### 5.1 AWS Lightsail Setup
- [ ] Provision Lightsail instance
- [ ] Install and configure MySQL
- [ ] Install Python and dependencies
- [ ] Set up virtual environment
- [ ] Clone Django repository
- [ ] Run migrations
- [ ] Create superuser account

### 5.2 Web Server Configuration
- [ ] Install and configure Nginx
- [ ] Set up Gunicorn for Django
- [ ] Configure reverse proxy
- [ ] Set up static files serving
- [ ] Configure media files handling

### 5.3 HTTPS & Domain
- [ ] Configure domain/subdomain
- [ ] Install Certbot
- [ ] Obtain SSL certificate (Let's Encrypt)
- [ ] Configure auto-renewal
- [ ] Test HTTPS redirection

### 5.4 CI/CD Pipeline
- [ ] Set up GitHub Actions for backend
  - [ ] Run tests on push
  - [ ] Deploy to staging/production
- [ ] Set up GitHub Actions for frontend
  - [ ] Build TypeScript/React
  - [ ] Deploy to GitHub Pages
- [ ] Configure deployment secrets

### 5.5 Monitoring & Logging
- [ ] Configure Django logging
- [ ] Set up error tracking (Sentry or similar)
- [ ] Configure Nginx access/error logs
- [ ] Set up database backup automation
- [ ] Configure uptime monitoring
- [ ] Set up alerts for critical errors

---

## Phase 6: Data Population & QA

### 6.1 Initial Data Load
- [ ] Run full import from Sheerpluck
- [ ] Run full import from IMSLP
- [ ] Review import logs and errors
- [ ] Manual review of sample records
- [ ] Fix critical data issues

### 6.2 Data Quality Assurance
- [ ] Staff review of composer entries
- [ ] Verification of work metadata
- [ ] Duplicate detection and merging
- [ ] Missing data identification
- [ ] Standardization of naming conventions

### 6.3 Admin Training
- [ ] Create admin user guide
- [ ] Document data entry standards
- [ ] Train staff on admin portal
- [ ] Set up roles and permissions
- [ ] Document curation workflows

---

## Phase 7: Launch Preparation

### 7.1 Testing & QA
- [ ] End-to-end testing of all features
- [ ] Performance testing (load times, API response)
- [ ] Security audit (SQL injection, XSS, CSRF)
- [ ] Accessibility audit (WCAG compliance)
- [ ] Mobile experience testing

### 7.2 Documentation
- [ ] User guide for public website
- [ ] API documentation (public endpoints)
- [ ] Admin portal documentation
- [ ] Developer setup guide (README)
- [ ] Data source attribution and licensing
- [ ] Privacy policy (if collecting user data)

### 7.3 Pre-Launch
- [ ] Configure production environment variables
- [ ] Final database backup
- [ ] Set up CDN (optional, for performance)
- [ ] Prepare launch announcement
- [ ] Set up analytics (Google Analytics or privacy-friendly alternative)

---

## Phase 8: Launch & Iteration

### 8.1 Soft Launch
- [ ] Deploy to production
- [ ] Test all features in production
- [ ] Internal review period
- [ ] Fix critical bugs
- [ ] Monitor server performance

### 8.2 Public Launch
- [ ] Announce to Baltimore Classical Guitar Society
- [ ] Announce to Peabody Institute
- [ ] Social media announcements
- [ ] Submit to relevant directories/catalogs
- [ ] Monitor user feedback

### 8.3 Post-Launch Monitoring
- [ ] Daily monitoring (first week)
- [ ] Track API usage and errors
- [ ] Monitor database performance
- [ ] Gather user feedback
- [ ] Create bug/feature tracking board

---

## Phase 9: Maintenance & Enhancement (Ongoing)

### 9.1 Regular Maintenance
- [ ] Weekly data quality reviews
- [ ] Monthly security updates
- [ ] Database optimization (indexes, queries)
- [ ] Backup verification
- [ ] SSL certificate renewal (automated, but verify)

### 9.2 Data Updates
- [ ] Establish schedule for re-scraping Sheerpluck/IMSLP
- [ ] Process staff-submitted corrections
- [ ] Add new composers/works
- [ ] Update metadata standards
- [ ] Archive old/deprecated records

### 9.3 Feature Enhancements (Future)
- [ ] User accounts and personalization
- [ ] Collaborative playlists
- [ ] Sheet music preview integration
- [ ] Recording/performance links
- [ ] Difficulty ratings and reviews
- [ ] Mobile app (React Native or PWA)
- [ ] Advanced music theory filtering (keys, forms, techniques)
- [ ] Export functionality (PDF, CSV, BibTeX)
- [ ] API for third-party integrations
- [ ] Community contributions (corrections, additions)

---

## Key Milestones

| Milestone | Target | Deliverable |
|-----------|--------|-------------|
| **M1: Project Kickoff** | Phase 1 | Schema design, repository setup |
| **M2: Data Acquisition** | Phase 2 | Sample data imported and profiled |
| **M3: Backend MVP** | Phase 3 | Working API and admin portal |
| **M4: Frontend MVP** | Phase 4 | Functional React application |
| **M5: Deployment** | Phase 5 | Staging environment live |
| **M6: Data Loaded** | Phase 6 | Full database populated and QA'd |
| **M7: Launch** | Phase 8 | Public website live |

---