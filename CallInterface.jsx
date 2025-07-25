import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PhoneCall } from 'lucide-react';

const CallInterface = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Call Interface</h1>
        <p className="text-gray-600">Make calls and manage conversations</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <PhoneCall className="h-5 w-5 mr-2" />
            Dialer
          </CardTitle>
          <CardDescription>
            Manual, Turbo, and Predictive dialing interface
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <PhoneCall className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Call Interface</h3>
            <p className="text-gray-500">Call interface features will be implemented here.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default CallInterface;

