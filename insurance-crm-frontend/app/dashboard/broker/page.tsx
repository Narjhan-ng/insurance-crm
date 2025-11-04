'use client';

import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * Broker Dashboard - Main dashboard for broker role
 *
 * This is a placeholder dashboard to test authentication flow.
 * In Phase 2, this will be replaced with:
 * - KPI cards (prospects, quotes, policies, commissions)
 * - Prospect list table
 * - Recent activity feed
 * - Quick action buttons
 */
export default function BrokerDashboard() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Broker Dashboard</h1>
            <p className="text-gray-600 mt-1">Welcome back, {user?.username}!</p>
          </div>
          <Button variant="outline" onClick={logout}>
            Sign Out
          </Button>
        </div>

        {/* User Info Card */}
        <Card>
          <CardHeader>
            <CardTitle>User Information</CardTitle>
            <CardDescription>Your current session details</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-semibold">Username:</span> {user?.username}
              </div>
              <div>
                <span className="font-semibold">Email:</span> {user?.email}
              </div>
              <div>
                <span className="font-semibold">Role:</span>{' '}
                <span className="capitalize">{user?.role}</span>
              </div>
              <div>
                <span className="font-semibold">Status:</span>{' '}
                {user?.is_active ? (
                  <span className="text-green-600">Active</span>
                ) : (
                  <span className="text-red-600">Inactive</span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Placeholder for future features */}
        <Card>
          <CardHeader>
            <CardTitle>Coming Soon</CardTitle>
            <CardDescription>Phase 2 features</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              <li>✅ <strong>Authentication</strong> - Completed</li>
              <li>⏳ <strong>Prospect Management</strong> - Coming in Phase 2</li>
              <li>⏳ <strong>Eligibility Checking</strong> - Coming in Phase 2</li>
              <li>⏳ <strong>AI Quote Generation</strong> - Coming in Phase 2</li>
              <li>⏳ <strong>Policy Management</strong> - Coming in Phase 3</li>
              <li>⏳ <strong>Commission Tracking</strong> - Coming in Phase 3</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
