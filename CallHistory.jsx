import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Phone } from 'lucide-react';

const CallHistory = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Call History</h1>
        <p className="text-gray-600">Review your previous calls</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Phone className="h-5 w-5 mr-2" />
            Call Records
          </CardTitle>
          <CardDescription>
            History of all your calls and outcomes
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <Phone className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Call History</h3>
            <p className="text-gray-500">Call history features will be implemented here.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default CallHistory;

