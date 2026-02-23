import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Login from './components/Login';
import Layout from './components/Layout';
import PrivateRoute from './components/PrivateRoute';
import Dashboard from './pages/Dashboard';
import FilesPage from './pages/FilesPage';
import JMeterPage from './pages/JMeterPage';
import WebVitalsPage from './pages/WebVitalsPage';
import AIChatPage from './pages/AIChatPage';
import ParsedDataPage from './pages/ParsedDataPage';
import BaselinesPage from './pages/BaselinesPage';
import ComparePage from './pages/ComparePage';
import ReleaseDecisionPage from './pages/ReleaseDecisionPage';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route
            path="/*"
            element={
              <PrivateRoute>
                <Layout />
              </PrivateRoute>
            }
          >
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="upload" element={<FilesPage />} />
            <Route path="files" element={<FilesPage />} />
            <Route path="jmeter" element={<JMeterPage />} />
            <Route path="web-vitals" element={<WebVitalsPage />} />
            <Route path="runs/:runId/parsed-data" element={<ParsedDataPage />} />
            <Route path="baselines" element={<BaselinesPage />} />
            <Route path="compare" element={<ComparePage />} />
            <Route path="release-decision" element={<ReleaseDecisionPage />} />
            <Route path="ai-chat" element={<AIChatPage />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;

