import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
import json
import socket
import threading
import time
from src.models import db, SipConfiguration, SipChannel, Call, CallEvent

logger = logging.getLogger(__name__)

class AsteriskAMIClient:
    """Asterisk Manager Interface client for telephony operations"""
    
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.socket = None
        self.connected = False
        self.authenticated = False
        self.event_handlers = {}
        self.response_handlers = {}
        self.action_id_counter = 0
        self.running = False
        self.thread = None
        
    def connect(self) -> bool:
        """Connect to Asterisk AMI"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            
            # Read welcome message
            welcome = self.socket.recv(1024).decode('utf-8')
            logger.info(f"AMI Welcome: {welcome.strip()}")
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to AMI: {e}")
            return False
    
    def authenticate(self) -> bool:
        """Authenticate with Asterisk AMI"""
        if not self.connected:
            return False
            
        try:
            action_id = self._get_action_id()
            login_message = (
                f"Action: Login\r\n"
                f"Username: {self.username}\r\n"
                f"Secret: {self.password}\r\n"
                f"ActionID: {action_id}\r\n\r\n"
            )
            
            self.socket.send(login_message.encode('utf-8'))
            
            # Read response
            response = self._read_response()
            if response and response.get('Response') == 'Success':
                self.authenticated = True
                logger.info("AMI authentication successful")
                return True
            else:
                logger.error(f"AMI authentication failed: {response}")
                return False
                
        except Exception as e:
            logger.error(f"AMI authentication error: {e}")
            return False
    
    def start_event_loop(self):
        """Start the event loop in a separate thread"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._event_loop, daemon=True)
        self.thread.start()
        logger.info("AMI event loop started")
    
    def stop_event_loop(self):
        """Stop the event loop"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("AMI event loop stopped")
    
    def _event_loop(self):
        """Main event loop for processing AMI events"""
        while self.running and self.connected:
            try:
                message = self._read_response()
                if message:
                    self._handle_message(message)
            except Exception as e:
                logger.error(f"Event loop error: {e}")
                time.sleep(1)
    
    def _read_response(self) -> Optional[Dict]:
        """Read a complete AMI response"""
        try:
            buffer = ""
            while True:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                buffer += data
                
                # Check for complete message (ends with \r\n\r\n)
                if '\r\n\r\n' in buffer:
                    message_text = buffer.split('\r\n\r\n')[0]
                    return self._parse_message(message_text)
                    
        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"Error reading AMI response: {e}")
            return None
    
    def _parse_message(self, message_text: str) -> Dict:
        """Parse AMI message into dictionary"""
        message = {}
        for line in message_text.split('\r\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                message[key.strip()] = value.strip()
        return message
    
    def _handle_message(self, message: Dict):
        """Handle incoming AMI message"""
        if 'Event' in message:
            # This is an event
            event_type = message['Event']
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        handler(message)
                    except Exception as e:
                        logger.error(f"Error in event handler for {event_type}: {e}")
        
        elif 'ActionID' in message:
            # This is a response to an action
            action_id = message['ActionID']
            if action_id in self.response_handlers:
                handler = self.response_handlers.pop(action_id)
                handler(message)
    
    def _get_action_id(self) -> str:
        """Generate unique action ID"""
        self.action_id_counter += 1
        return f"action_{self.action_id_counter}_{int(time.time())}"
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler for specific event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def send_action(self, action: str, parameters: Dict = None, callback: Callable = None) -> str:
        """Send AMI action"""
        if not self.authenticated:
            raise Exception("Not authenticated with AMI")
        
        action_id = self._get_action_id()
        message = f"Action: {action}\r\nActionID: {action_id}\r\n"
        
        if parameters:
            for key, value in parameters.items():
                message += f"{key}: {value}\r\n"
        
        message += "\r\n"
        
        if callback:
            self.response_handlers[action_id] = callback
        
        self.socket.send(message.encode('utf-8'))
        return action_id
    
    def originate_call(self, channel: str, context: str, extension: str, priority: int = 1, 
                      caller_id: str = None, variables: Dict = None, callback: Callable = None) -> str:
        """Originate a call through AMI"""
        parameters = {
            'Channel': channel,
            'Context': context,
            'Exten': extension,
            'Priority': priority
        }
        
        if caller_id:
            parameters['CallerID'] = caller_id
        
        if variables:
            for key, value in variables.items():
                parameters[f'Variable'] = f"{key}={value}"
        
        return self.send_action('Originate', parameters, callback)
    
    def hangup_call(self, channel: str, callback: Callable = None) -> str:
        """Hangup a call"""
        parameters = {'Channel': channel}
        return self.send_action('Hangup', parameters, callback)
    
    def get_channel_status(self, channel: str, callback: Callable = None) -> str:
        """Get channel status"""
        parameters = {'Channel': channel}
        return self.send_action('Status', parameters, callback)
    
    def disconnect(self):
        """Disconnect from AMI"""
        self.running = False
        self.authenticated = False
        self.connected = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        logger.info("Disconnected from AMI")

class SipService:
    """Service for managing SIP configurations and telephony operations"""
    
    def __init__(self):
        self.ami_clients = {}  # Configuration ID -> AMI Client
        self.active_calls = {}  # Call ID -> Call info
        self.event_callbacks = []
        
    def get_active_configuration(self) -> Optional[SipConfiguration]:
        """Get the currently active SIP configuration"""
        return SipConfiguration.query.filter_by(is_active=True).first()
    
    def test_sip_configuration(self, config_id: int) -> Dict:
        """Test SIP configuration connectivity"""
        config = SipConfiguration.query.get(config_id)
        if not config:
            return {'success': False, 'message': 'Configuration not found'}
        
        try:
            # Create temporary AMI client for testing
            ami_client = AsteriskAMIClient(
                host=config.host,
                port=config.port,
                username=config.username,
                password=config.password_encrypted  # In production, decrypt this
            )
            
            # Test connection
            if not ami_client.connect():
                return {'success': False, 'message': 'Failed to connect to AMI'}
            
            # Test authentication
            if not ami_client.authenticate():
                ami_client.disconnect()
                return {'success': False, 'message': 'Authentication failed'}
            
            ami_client.disconnect()
            
            # Update test status
            config.last_tested = datetime.utcnow()
            config.test_status = 'success'
            config.test_message = 'Connection successful'
            db.session.commit()
            
            return {'success': True, 'message': 'Connection successful'}
            
        except Exception as e:
            # Update test status
            config.last_tested = datetime.utcnow()
            config.test_status = 'failed'
            config.test_message = str(e)
            db.session.commit()
            
            return {'success': False, 'message': str(e)}
    
    def initialize_ami_connection(self, config_id: int) -> bool:
        """Initialize AMI connection for a configuration"""
        config = SipConfiguration.query.get(config_id)
        if not config:
            return False
        
        try:
            ami_client = AsteriskAMIClient(
                host=config.host,
                port=config.port,
                username=config.username,
                password=config.password_encrypted  # In production, decrypt this
            )
            
            if ami_client.connect() and ami_client.authenticate():
                # Register event handlers
                ami_client.register_event_handler('Newchannel', self._handle_new_channel)
                ami_client.register_event_handler('Hangup', self._handle_hangup)
                ami_client.register_event_handler('Bridge', self._handle_bridge)
                ami_client.register_event_handler('DialBegin', self._handle_dial_begin)
                ami_client.register_event_handler('DialEnd', self._handle_dial_end)
                
                # Start event loop
                ami_client.start_event_loop()
                
                self.ami_clients[config_id] = ami_client
                logger.info(f"AMI connection initialized for config {config_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize AMI connection: {e}")
            return False
    
    def originate_call(self, phone_number: str, agent_channel: str, call_id: int) -> bool:
        """Originate a call to a phone number"""
        active_config = self.get_active_configuration()
        if not active_config:
            logger.error("No active SIP configuration found")
            return False
        
        ami_client = self.ami_clients.get(active_config.id)
        if not ami_client:
            logger.error("AMI client not initialized")
            return False
        
        try:
            # Create channel name for outbound call
            channel = f"SIP/{active_config.username}/{phone_number}"
            
            # Set up call variables
            variables = {
                'CALL_ID': str(call_id),
                'AGENT_CHANNEL': agent_channel,
                'PHONE_NUMBER': phone_number
            }
            
            # Originate the call
            action_id = ami_client.originate_call(
                channel=channel,
                context='default',  # Configure based on your Asterisk setup
                extension=phone_number,
                caller_id=f"<{phone_number}>",
                variables=variables,
                callback=lambda response: self._handle_originate_response(response, call_id)
            )
            
            # Store call information
            self.active_calls[call_id] = {
                'channel': channel,
                'phone_number': phone_number,
                'agent_channel': agent_channel,
                'action_id': action_id,
                'started_at': datetime.utcnow()
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to originate call: {e}")
            return False
    
    def hangup_call(self, call_id: int) -> bool:
        """Hangup a call"""
        if call_id not in self.active_calls:
            return False
        
        call_info = self.active_calls[call_id]
        active_config = self.get_active_configuration()
        
        if not active_config:
            return False
        
        ami_client = self.ami_clients.get(active_config.id)
        if not ami_client:
            return False
        
        try:
            ami_client.hangup_call(
                channel=call_info['channel'],
                callback=lambda response: self._handle_hangup_response(response, call_id)
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to hangup call: {e}")
            return False
    
    def _handle_originate_response(self, response: Dict, call_id: int):
        """Handle response from originate action"""
        logger.info(f"Originate response for call {call_id}: {response}")
        
        # Create call event
        call_event = CallEvent(
            call_id=call_id,
            event_type='originate_response',
            timestamp=datetime.utcnow()
        )
        call_event.set_event_data(response)
        
        db.session.add(call_event)
        db.session.commit()
        
        # Notify event callbacks
        self._notify_event_callbacks('originate_response', {
            'call_id': call_id,
            'response': response
        })
    
    def _handle_new_channel(self, event: Dict):
        """Handle new channel event"""
        logger.info(f"New channel event: {event}")
        
        # Extract call ID from channel variables if available
        call_id = event.get('Variable', {}).get('CALL_ID')
        if call_id:
            call_event = CallEvent(
                call_id=int(call_id),
                event_type='new_channel',
                timestamp=datetime.utcnow()
            )
            call_event.set_event_data(event)
            
            db.session.add(call_event)
            db.session.commit()
    
    def _handle_hangup(self, event: Dict):
        """Handle hangup event"""
        logger.info(f"Hangup event: {event}")
        
        channel = event.get('Channel')
        if channel:
            # Find call by channel
            for call_id, call_info in self.active_calls.items():
                if call_info['channel'] == channel:
                    # Update call status
                    call = Call.query.get(call_id)
                    if call:
                        call.call_status = 'completed'
                        call.ended_at = datetime.utcnow()
                        call.calculate_duration()
                        
                        # Create call event
                        call_event = CallEvent(
                            call_id=call_id,
                            event_type='hangup',
                            timestamp=datetime.utcnow()
                        )
                        call_event.set_event_data(event)
                        
                        db.session.add(call_event)
                        db.session.commit()
                        
                        # Remove from active calls
                        del self.active_calls[call_id]
                        
                        # Notify event callbacks
                        self._notify_event_callbacks('call_ended', {
                            'call_id': call_id,
                            'event': event
                        })
                    break
    
    def _handle_bridge(self, event: Dict):
        """Handle bridge event (call answered)"""
        logger.info(f"Bridge event: {event}")
        
        # Extract call information from bridge event
        channel1 = event.get('Channel1')
        channel2 = event.get('Channel2')
        
        # Find matching call
        for call_id, call_info in self.active_calls.items():
            if call_info['channel'] in [channel1, channel2]:
                # Update call status
                call = Call.query.get(call_id)
                if call:
                    call.call_status = 'answered'
                    call.answered_at = datetime.utcnow()
                    
                    # Create call event
                    call_event = CallEvent(
                        call_id=call_id,
                        event_type='bridge',
                        timestamp=datetime.utcnow()
                    )
                    call_event.set_event_data(event)
                    
                    db.session.add(call_event)
                    db.session.commit()
                    
                    # Notify event callbacks
                    self._notify_event_callbacks('call_answered', {
                        'call_id': call_id,
                        'event': event
                    })



                break
    
    def _handle_dial_begin(self, event: Dict):
        """Handle dial begin event"""
        logger.info(f"Dial begin event: {event}")
        
        # Extract call information
        channel = event.get('Channel')
        destination = event.get('DestChannel')
        
        # Find matching call
        for call_id, call_info in self.active_calls.items():
            if call_info['channel'] == channel:
                # Update call status
                call = Call.query.get(call_id)
                if call:
                    call.call_status = 'ringing'
                    
                    # Create call event
                    call_event = CallEvent(
                        call_id=call_id,
                        event_type='dial_begin',
                        timestamp=datetime.utcnow()
                    )
                    call_event.set_event_data(event)
                    
                    db.session.add(call_event)
                    db.session.commit()
                    
                    # Notify event callbacks
                    self._notify_event_callbacks('call_ringing', {
                        'call_id': call_id,
                        'event': event
                    })
                break
    
    def _handle_dial_end(self, event: Dict):
        """Handle dial end event"""
        logger.info(f"Dial end event: {event}")
        
        channel = event.get('Channel')
        dial_status = event.get('DialStatus')
        
        # Find matching call
        for call_id, call_info in self.active_calls.items():
            if call_info['channel'] == channel:
                # Update call status based on dial status
                call = Call.query.get(call_id)
                if call:
                    if dial_status == 'ANSWER':
                        call.call_status = 'answered'
                        call.answered_at = datetime.utcnow()
                    elif dial_status in ['BUSY', 'CONGESTION']:
                        call.call_status = 'busy'
                        call.ended_at = datetime.utcnow()
                    elif dial_status in ['NOANSWER', 'CANCEL']:
                        call.call_status = 'no_answer'
                        call.ended_at = datetime.utcnow()
                    else:
                        call.call_status = 'failed'
                        call.ended_at = datetime.utcnow()
                    
                    # Create call event
                    call_event = CallEvent(
                        call_id=call_id,
                        event_type='dial_end',
                        timestamp=datetime.utcnow()
                    )
                    call_event.set_event_data(event)
                    
                    db.session.add(call_event)
                    db.session.commit()
                    
                    # If call didn't connect, remove from active calls
                    if dial_status != 'ANSWER':
                        del self.active_calls[call_id]
                    
                    # Notify event callbacks
                    self._notify_event_callbacks('dial_end', {
                        'call_id': call_id,
                        'dial_status': dial_status,
                        'event': event
                    })
                break
    
    def _handle_hangup_response(self, response: Dict, call_id: int):
        """Handle response from hangup action"""
        logger.info(f"Hangup response for call {call_id}: {response}")
        
        # Create call event
        call_event = CallEvent(
            call_id=call_id,
            event_type='hangup_response',
            timestamp=datetime.utcnow()
        )
        call_event.set_event_data(response)
        
        db.session.add(call_event)
        db.session.commit()
    
    def register_event_callback(self, callback: Callable):
        """Register callback for telephony events"""
        self.event_callbacks.append(callback)
    
    def _notify_event_callbacks(self, event_type: str, data: Dict):
        """Notify all registered event callbacks"""
        for callback in self.event_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
    
    def get_active_calls(self) -> Dict:
        """Get all active calls"""
        return self.active_calls.copy()
    
    def get_call_status(self, call_id: int) -> Optional[Dict]:
        """Get status of a specific call"""
        if call_id in self.active_calls:
            return self.active_calls[call_id].copy()
        return None
    
    def shutdown(self):
        """Shutdown all AMI connections"""
        for config_id, ami_client in self.ami_clients.items():
            try:
                ami_client.stop_event_loop()
                ami_client.disconnect()
            except Exception as e:
                logger.error(f"Error shutting down AMI client {config_id}: {e}")
        
        self.ami_clients.clear()
        self.active_calls.clear()
        logger.info("SIP service shutdown complete")

# Global SIP service instance
sip_service = SipService()

