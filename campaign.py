from src.models.user import db
from datetime import datetime, time

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft', nullable=False)
    dialer_mode = db.Column(db.String(20), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    daily_start_time = db.Column(db.Time)
    daily_end_time = db.Column(db.Time)
    timezone = db.Column(db.String(50), default='UTC')
    max_attempts = db.Column(db.Integer, default=3)
    retry_delay_minutes = db.Column(db.Integer, default=60)
    predictive_ratio = db.Column(db.Numeric(3, 2), default=1.2)
    turbo_delay_seconds = db.Column(db.Integer, default=5)
    
    # Relationships
    leads = db.relationship('Lead', backref='campaign', lazy=True, cascade='all, delete-orphan')
    calls = db.relationship('Call', backref='campaign', lazy=True)
    assignments = db.relationship('CampaignAssignment', backref='campaign', lazy=True, cascade='all, delete-orphan')
    statistics = db.relationship('CampaignStatistics', backref='campaign', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Campaign {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'dialer_mode': self.dialer_mode,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'daily_start_time': self.daily_start_time.strftime('%H:%M:%S') if self.daily_start_time else None,
            'daily_end_time': self.daily_end_time.strftime('%H:%M:%S') if self.daily_end_time else None,
            'timezone': self.timezone,
            'max_attempts': self.max_attempts,
            'retry_delay_minutes': self.retry_delay_minutes,
            'predictive_ratio': float(self.predictive_ratio) if self.predictive_ratio else None,
            'turbo_delay_seconds': self.turbo_delay_seconds,
            'leads_count': len(self.leads) if self.leads else 0,
            'calls_made': len(self.calls) if self.calls else 0
        }

class CampaignAssignment(db.Model):
    __tablename__ = 'campaign_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Unique constraint to prevent duplicate assignments
    __table_args__ = (db.UniqueConstraint('campaign_id', 'user_id', name='unique_campaign_user'),)
    
    def __repr__(self):
        return f'<CampaignAssignment Campaign:{self.campaign_id} User:{self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'user_id': self.user_id,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'assigned_by': self.assigned_by
        }

class CampaignStatistics(db.Model):
    __tablename__ = 'campaign_statistics'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    total_calls = db.Column(db.Integer, default=0)
    successful_calls = db.Column(db.Integer, default=0)
    failed_calls = db.Column(db.Integer, default=0)
    total_duration_seconds = db.Column(db.Integer, default=0)
    leads_contacted = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint for campaign and date
    __table_args__ = (db.UniqueConstraint('campaign_id', 'date', name='unique_campaign_date'),)
    
    def __repr__(self):
        return f'<CampaignStatistics Campaign:{self.campaign_id} Date:{self.date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'date': self.date.isoformat() if self.date else None,
            'total_calls': self.total_calls,
            'successful_calls': self.successful_calls,
            'failed_calls': self.failed_calls,
            'total_duration_seconds': self.total_duration_seconds,
            'leads_contacted': self.leads_contacted,
            'conversions': self.conversions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'success_rate': self.successful_calls / self.total_calls if self.total_calls > 0 else 0,
            'conversion_rate': self.conversions / self.leads_contacted if self.leads_contacted > 0 else 0
        }

