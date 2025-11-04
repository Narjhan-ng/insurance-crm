'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { toast } from 'sonner';

/**
 * Zod validation schema for registration form
 * Enforces:
 * - Username: min 3 chars
 * - Email: valid email format
 * - Password: min 8 chars
 * - Role: one of allowed values (broker, manager, admin, affiliate)
 */
const registerSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  role: z.enum(['broker', 'manager', 'admin', 'affiliate'], {
    errorMap: () => ({ message: 'Please select a valid role' }),
  }),
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      role: 'broker', // Default role is broker
    },
  });

  /**
   * Handles user registration
   *
   * Flow:
   * 1. POST registration data to /auth/register
   * 2. Backend creates user account
   * 3. Automatically log in with username/password
   * 4. Redirect to dashboard
   */
  const onSubmit = async (data: RegisterForm) => {
    setLoading(true);
    try {
      // Step 1: Register new user
      await api.post('/auth/register', {
        username: data.username,
        email: data.email,
        password: data.password,
        role: data.role,
      });

      // Step 2: Automatically log in after registration (use form-data for OAuth2)
      const loginFormData = new URLSearchParams();
      loginFormData.append('username', data.username);
      loginFormData.append('password', data.password);

      const loginResponse = await api.post('/auth/login', loginFormData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      const { access_token } = loginResponse.data;

      // Step 3: Save token and fetch user data
      await login(access_token);

      // Step 4: Show success message
      toast.success('Registration successful', {
        description: 'Your account has been created!',
      });

      // Step 5: Navigate to dashboard
      router.push('/dashboard/broker');
    } catch (error: any) {
      // Error handling: could be duplicate username, email, etc.
      toast.error('Registration failed', {
        description: error.response?.data?.detail || 'Please try again',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-8">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">Create an account</CardTitle>
          <CardDescription>
            Enter your information to get started
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Username field */}
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                {...register('username')}
                placeholder="Choose a username"
                disabled={loading}
              />
              {errors.username && (
                <p className="text-sm text-red-500">{errors.username.message}</p>
              )}
            </div>

            {/* Email field */}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                {...register('email')}
                placeholder="your@email.com"
                disabled={loading}
              />
              {errors.email && (
                <p className="text-sm text-red-500">{errors.email.message}</p>
              )}
            </div>

            {/* Password field */}
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                {...register('password')}
                placeholder="Create a password"
                disabled={loading}
              />
              {errors.password && (
                <p className="text-sm text-red-500">{errors.password.message}</p>
              )}
            </div>

            {/* Role selection */}
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <select
                id="role"
                {...register('role')}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={loading}
              >
                <option value="broker">Broker</option>
                <option value="manager">Manager</option>
                <option value="admin">Admin</option>
                <option value="affiliate">Affiliate</option>
              </select>
              {errors.role && (
                <p className="text-sm text-red-500">{errors.role.message}</p>
              )}
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Creating account...' : 'Create account'}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex flex-col space-y-2">
          <div className="text-sm text-center text-gray-600">
            Already have an account?{' '}
            <Link href="/login" className="text-blue-600 hover:underline">
              Sign in here
            </Link>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
