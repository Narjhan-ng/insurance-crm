import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * Homepage - Landing page for the Insurance CRM
 *
 * This is a simple landing page that redirects users to login or register.
 * In a production app, this would contain marketing content, features, etc.
 */
export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
      <Card className="w-full max-w-2xl">
        <CardHeader className="text-center space-y-4">
          <CardTitle className="text-4xl font-bold">Insurance CRM</CardTitle>
          <CardDescription className="text-lg">
            AI-Powered Insurance Management System
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div className="space-y-2">
              <h3 className="font-semibold">✨ Key Features:</h3>
              <ul className="list-disc list-inside space-y-1 text-gray-600">
                <li>Prospect Management</li>
                <li>Eligibility Checking (4 providers)</li>
                <li>AI-Powered Quote Generation</li>
                <li>Policy Management</li>
                <li>Commission Tracking</li>
                <li>Advanced Analytics</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold">🎯 User Roles:</h3>
              <ul className="list-disc list-inside space-y-1 text-gray-600">
                <li>Broker - Manage prospects & quotes</li>
                <li>Manager - Team oversight</li>
                <li>Admin - Full system control</li>
                <li>Affiliate - Partner access</li>
              </ul>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 pt-4">
            <Link href="/login" className="flex-1">
              <Button className="w-full" size="lg">
                Sign In
              </Button>
            </Link>
            <Link href="/register" className="flex-1">
              <Button variant="outline" className="w-full" size="lg">
                Create Account
              </Button>
            </Link>
          </div>

          <div className="text-center text-sm text-gray-500 pt-4">
            <p>Powered by Next.js, FastAPI, and Claude AI</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
