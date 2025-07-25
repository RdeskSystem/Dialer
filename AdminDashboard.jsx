import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Users, 
  PhoneCall, 
  TrendingUp, 
  Clock,
  Phone,
  UserCheck,
  Activity,
  BarChart3
} from 'lucide-react';
import { apiService } from '../../lib/api';
import LoadingSpinner from '../ui/LoadingSpinner';

const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      // Fetch various dashboard data
      const [campaignsData, usersData, callsData, sipStatus] = await Promise.all([
        apiService.getCampaigns({ limit: 5 }),
        apiService.getUsers({ limit: 10 }),
        apiService.getCallStats(),
        apiService.getSipStatus().catch(() => ({ active_configuration: null }))
      ]);

      setStats({
        campaigns: campaignsData,
        users: usersData,
        calls: callsData,
        sip: sipStatus
      });
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Error loading dashboard: {error}</p>
        <Button onClick={fetchDashboardData} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Total Campaigns',
      value: stats?.campaigns?.total || 0,
      icon: PhoneCall,
      description: 'Active campaigns',
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      title: 'Total Users',
      value: stats?.users?.total || 0,
      icon: Users,
      description: 'Registered users',
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      title: 'Calls Today',
      value: stats?.calls?.total_calls || 0,
      icon: Phone,
      description: 'Total calls made',
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
    },
    {
      title: 'Answer Rate',
      value: `${Math.round((stats?.calls?.answer_rate || 0) * 100)}%`,
      icon: TrendingUp,
      description: 'Call success rate',
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600">Overview of your call center operations</p>
        </div>
        <Button onClick={fetchDashboardData}>
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card key={index}>
              <CardContent className="p-6">
                <div className="flex items-center">
                  <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                    <Icon className={`h-6 w-6 ${stat.color}`} />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                    <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                    <p className="text-xs text-gray-500">{stat.description}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SIP Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Phone className="h-5 w-5 mr-2" />
              SIP Configuration
            </CardTitle>
            <CardDescription>
              Current telephony system status
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stats?.sip?.active_configuration ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Status</span>
                  <Badge variant="default" className="bg-green-100 text-green-800">
                    Connected
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Configuration</span>
                  <span className="text-sm text-gray-600">
                    {stats.sip.active_configuration.name}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Active Calls</span>
                  <span className="text-sm text-gray-600">
                    {stats.sip.active_calls_count || 0}
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-center py-4">
                <Badge variant="destructive">Not Configured</Badge>
                <p className="text-sm text-gray-500 mt-2">
                  No active SIP configuration found
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Activity className="h-5 w-5 mr-2" />
              Recent Activity
            </CardTitle>
            <CardDescription>
              Latest system activities
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center space-x-3">
                <div className="h-2 w-2 bg-blue-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">System started</p>
                  <p className="text-xs text-gray-500">2 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="h-2 w-2 bg-green-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Admin user logged in</p>
                  <p className="text-xs text-gray-500">5 minutes ago</p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="h-2 w-2 bg-gray-400 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Database initialized</p>
                  <p className="text-xs text-gray-500">10 minutes ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Common administrative tasks
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Button variant="outline" className="h-20 flex flex-col items-center justify-center">
              <PhoneCall className="h-6 w-6 mb-2" />
              Create Campaign
            </Button>
            <Button variant="outline" className="h-20 flex flex-col items-center justify-center">
              <UserCheck className="h-6 w-6 mb-2" />
              Add User
            </Button>
            <Button variant="outline" className="h-20 flex flex-col items-center justify-center">
              <BarChart3 className="h-6 w-6 mb-2" />
              View Analytics
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminDashboard;

