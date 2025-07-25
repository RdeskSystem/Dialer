import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Phone } from 'lucide-react';

const SipConfiguration = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">SIP Configuration</h1>
        <p className="text-gray-600">Configure telephony settings</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Phone className="h-5 w-5 mr-2" />
            SIP Settings
          </CardTitle>
          <CardDescription>
            Configure SIP trunk and Asterisk settings
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <Phone className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">SIP Configuration</h3>
            <p className="text-gray-500">SIP configuration features will be implemented here.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SipConfiguration;

