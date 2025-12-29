# User Credentials

## Primary User Account

### Your Account
- **Username**: `raghskmr`
- **Password**: `password`
- **Email**: raghskmr@autoreportanalyzer.com
- **Role**: Performance Architect

## Login Instructions

1. Open the application at: **http://localhost:3000**
2. Enter credentials:
   ```
   Username: raghskmr
   Password: password
   ```
3. Click "Login"

## Demo Access

For testing purposes, any username with password `password` will also work.

### Examples:
- Username: `demo` | Password: `password`
- Username: `test` | Password: `password`
- Username: `admin` | Password: `password`

## User Features

As a logged-in user, you can:
- ✅ View Dashboard with statistics
- ✅ Upload performance data files
- ✅ Analyze uploaded files
- ✅ Generate comprehensive reports
- ✅ Manage all your files

## Security Notes

**For Production Deployment**:
1. Replace demo authentication with proper backend API
2. Implement JWT tokens
3. Use secure password hashing (bcrypt)
4. Enable HTTPS
5. Add password complexity requirements
6. Implement session timeout
7. Add 2FA (optional)

**Current Implementation**:
- Demo authentication (client-side only)
- Session stored in localStorage
- No password encryption
- Suitable for development/testing only

## Changing Password

To change the password in development:
1. Edit `frontend/src/context/AuthContext.tsx`
2. Update the `predefinedUsers` object:
   ```typescript
   'raghskmr': {
     password: 'your_new_password',
     email: 'raghskmr@autoreportanalyzer.com',
     role: 'Performance Architect'
   }
   ```
3. Save and refresh browser

## Adding More Users

To add additional predefined users, edit `AuthContext.tsx`:

```typescript
const predefinedUsers: Record<string, { password: string; email: string; role: string }> = {
  'raghskmr': {
    password: 'password',
    email: 'raghskmr@autoreportanalyzer.com',
    role: 'Performance Architect'
  },
  'john': {
    password: 'john123',
    email: 'john@example.com',
    role: 'Performance Engineer'
  },
  'admin': {
    password: 'admin123',
    email: 'admin@example.com',
    role: 'Administrator'
  }
};
```

## Session Management

- **Session Duration**: Until browser tab is closed or logout clicked
- **Auto-login**: Yes (if previous session exists)
- **Multi-device**: No (localStorage is browser-specific)
- **Session Storage**: Browser localStorage

### Clear Session
To manually clear your session:
1. Open browser console (F12)
2. Run: `localStorage.clear()`
3. Refresh page

## Logout

Click the logout button at the bottom of the sidebar to end your session.

## Troubleshooting

### Can't login?
- Verify username: `raghskmr` (lowercase, no spaces)
- Verify password: `password` (lowercase)
- Check browser console for errors (F12)
- Try clearing browser cache

### Session expires immediately?
- Check if cookies/localStorage are enabled
- Try incognito/private browsing mode
- Clear browser cache and try again

### Forgot password?
For demo: Use any username with password `password`
For production: Implement password reset functionality

## Your Account Details

**Name**: Raghvendra Kumar (raghskmr)
**Access Level**: Full access to all features
**Default Dashboard**: Shows all performance metrics
**File Storage**: All uploaded files visible

Enjoy your personalized Performance Analysis Platform! 🚀












