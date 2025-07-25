import React, { useState } from 'react';
import { Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { 
  Phone, 
  PhoneCall, 
  Users, 
  BarChart3, 
  Menu,
  X,
  LogOut,
  Bell,
  User
} from 'lucide-react';

// Import agent pages (we'll create these next)
import AgentDashboard from '../agent/AgentDashboard';
import CallInterface from '../agent/CallInterface';
import LeadsList from '../agent/LeadsList';
import CallHistory from '../agent/CallHistory';

const AgentLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();

  const navigation = [
    {
      name: 'Dashboard',
      href: '/agent',
      icon: BarChart3,
      exact: true,
    },
    {
      name: 'Call Interface',
      href: '/agent/call',
      icon: PhoneCall,
    },
    {
      name: 'Leads',
      href: '/agent/leads',
      icon: Users,
    },
    {
      name: 'Call History',
      href: '/agent/history',
      icon: Phone,
    },
  ];

  const isCurrentPath = (path, exact = false) => {
    if (exact) {
      return location.pathname === path;
    }
    return location.pathname.startsWith(path);
  };

  const handleLogout = async () => {
    await logout();
  };

  return (
    <div className="h-screen flex overflow-hidden bg-gray-100">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 flex z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        >
          <div className="fixed inset-0 bg-gray-600 bg-opacity-75" />
        </div>
      )}

      {/* Sidebar */}
      <div className={`${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      } fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out md:translate-x-0 md:static md:inset-0`}>
        
        {/* Sidebar header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
          <div className="flex items-center">
            <Phone className="h-8 w-8 text-green-600" />
            <span className="ml-2 text-xl font-semibold text-gray-900">
              Agent Portal
            </span>
          </div>
          <button
            className="md:hidden"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-6 w-6 text-gray-400" />
          </button>
        </div>

        {/* Agent Status */}
        <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center">
            <div className="h-3 w-3 bg-green-400 rounded-full mr-2"></div>
            <span className="text-sm font-medium text-gray-900">Available</span>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Ready for calls
          </div>
        </div>

        {/* Navigation */}
        <nav className="mt-5 px-2">
          <div className="space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const current = isCurrentPath(item.href, item.exact);
              
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`${
                    current
                      ? 'bg-green-100 border-green-500 text-green-700'
                      : 'border-transparent text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  } group flex items-center px-2 py-2 text-sm font-medium rounded-md border-l-4 transition-colors duration-150`}
                  onClick={() => setSidebarOpen(false)}
                >
                  <Icon
                    className={`${
                      current ? 'text-green-500' : 'text-gray-400 group-hover:text-gray-500'
                    } mr-3 h-5 w-5`}
                  />
                  {item.name}
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Quick Stats */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <div className="text-xs text-gray-500 space-y-1">
            <div className="flex justify-between">
              <span>Calls Today:</span>
              <span className="font-medium">0</span>
            </div>
            <div className="flex justify-between">
              <span>Talk Time:</span>
              <span className="font-medium">0m</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-col w-0 flex-1 overflow-hidden">
        {/* Top navigation */}
        <div className="relative z-10 flex-shrink-0 flex h-16 bg-white shadow">
          <button
            className="px-4 border-r border-gray-200 text-gray-500 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-green-500 md:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </button>
          
          <div className="flex-1 px-4 flex justify-between">
            <div className="flex-1 flex items-center">
              <h1 className="text-lg font-semibold text-gray-900">
                {navigation.find(nav => isCurrentPath(nav.href, nav.exact))?.name || 'Agent Portal'}
              </h1>
            </div>
            
            <div className="ml-4 flex items-center md:ml-6">
              {/* Notifications */}
              <button className="bg-white p-1 rounded-full text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500">
                <Bell className="h-6 w-6" />
              </button>

              {/* User menu */}
              <div className="ml-3 relative">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 rounded-full bg-green-600 flex items-center justify-center">
                      <User className="h-4 w-4 text-white" />
                    </div>
                  </div>
                  <div className="hidden md:block">
                    <div className="text-sm font-medium text-gray-900">
                      {user?.first_name} {user?.last_name}
                    </div>
                    <div className="text-xs text-gray-500">
                      Agent
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleLogout}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="flex-1 relative overflow-y-auto focus:outline-none">
          <div className="py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
              <Routes>
                <Route index element={<AgentDashboard />} />
                <Route path="call/*" element={<CallInterface />} />
                <Route path="leads/*" element={<LeadsList />} />
                <Route path="history/*" element={<CallHistory />} />
                <Route path="*" element={<Navigate to="/agent" replace />} />
              </Routes>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default AgentLayout;

