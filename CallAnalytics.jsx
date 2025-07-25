import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart3 } from 'lucide-react';

const CallAnalytics = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Call Analytics</h1>
        <p className="text-gray-600">Performance analytics and reporting</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <BarChart3 className="h-5 w-5 mr-2" />
            Analytics
          </CardTitle>
          <CardDescription>
            Real-time performance metrics and reports
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Call Analytics</h3>
            <p className="text-gray-500">Analytics features will be implemented here.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default CallAnalytics;

