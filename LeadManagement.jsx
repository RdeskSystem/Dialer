import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Database } from 'lucide-react';

const LeadManagement = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Lead Management</h1>
        <p className="text-gray-600">Import and manage leads</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Database className="h-5 w-5 mr-2" />
            Leads
          </CardTitle>
          <CardDescription>
            Import leads from XLSX and manage contact data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Lead Management</h3>
            <p className="text-gray-500">Lead management features will be implemented here.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default LeadManagement;

