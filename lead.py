from src.models.user import db
from datetime import datetime
import json

class Lead(db.Model):
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(255))
    company = db.Column(db.String(255))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    country = db.Column(db.String(100), default='US')
    status = db.Column(db.String(20), default='new')
    priority = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_contacted = db.Column(db.DateTime)
    next_contact_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    custom_fields = db.Column(db.Text)  # JSON string for flexible custom data
    
    # Relationships
    calls = db.relationship('Call', backref='lead', lazy=True)
    history = db.relationship('LeadHistory', backref='lead', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Lead {self.first_name} {self.last_name} - {self.phone_number}>'
    
    def get_custom_fields(self):
        """Parse custom fields JSON"""
        if self.custom_fields:
            try:
                return json.loads(self.custom_fields)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_custom_fields(self, fields_dict):
        """Set custom fields as JSON"""
        self.custom_fields = json.dumps(fields_dict) if fields_dict else None
    
    def get_call_count(self):
        """Get the number of calls made to this lead"""
        return len(self.calls) if self.calls else 0
    
    def get_last_call_outcome(self):
        """Get the outcome of the most recent call"""
        if self.calls:
            last_call = max(self.calls, key=lambda c: c.started_at)
            return last_call.call_outcome
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone_number': self.phone_number,
            'email': self.email,
            'company': self.company,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'country': self.country,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_contacted': self.last_contacted.isoformat() if self.last_contacted else None,
            'next_contact_date': self.next_contact_date.isoformat() if self.next_contact_date else None,
            'notes': self.notes,
            'custom_fields': self.get_custom_fields(),
            'call_count': self.get_call_count(),
            'last_call_outcome': self.get_last_call_outcome()
        }

class LeadHistory(db.Model):
    __tablename__ = 'lead_history'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    field_name = db.Column(db.String(100), nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LeadHistory Lead:{self.lead_id} Field:{self.field_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'field_name': self.field_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'changed_by': self.changed_by,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None
        }

