-- Migration: Add reports table for tracking generated reports
-- Date: 2025-10-30
-- Description: Reports module for sales, commission, and performance analytics

CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    report_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    generated_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    format VARCHAR(10) NOT NULL,
    file_path VARCHAR(500),
    filters TEXT,
    record_count INTEGER,

    -- Indexes for performance
    CONSTRAINT reports_report_type_check CHECK (report_type IN (
        'sales_summary',
        'commission_breakdown',
        'broker_performance',
        'pipeline_analysis',
        'provider_comparison'
    )),
    CONSTRAINT reports_format_check CHECK (format IN ('pdf', 'csv', 'json'))
);

CREATE INDEX idx_reports_type ON reports(report_type);
CREATE INDEX idx_reports_generated_by ON reports(generated_by);
CREATE INDEX idx_reports_generated_at ON reports(generated_at DESC);

-- Add comment
COMMENT ON TABLE reports IS 'Stores metadata for generated business intelligence reports';
COMMENT ON COLUMN reports.report_type IS 'Type of report: sales_summary, commission_breakdown, broker_performance, etc.';
COMMENT ON COLUMN reports.filters IS 'JSON string of applied filters';
COMMENT ON COLUMN reports.file_path IS 'Path to exported file (PDF/CSV)';
