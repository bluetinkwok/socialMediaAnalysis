/**
 * Application context for managing global state
 */

import React, { createContext, useContext, useReducer } from 'react';
import type { ReactNode } from 'react';
import type { Platform, Content, DownloadJob, User } from '../types';

// State interface
interface AppState {
  user: User | null;
  isAuthenticated: boolean;
  selectedPlatforms: Platform[];
  currentPage: string;
  downloadJobs: DownloadJob[];
  recentContent: Content[];
  isLoading: boolean;
  error: string | null;
}

// Action types
type AppAction = 
  | { type: 'SET_USER'; payload: User | null }
  | { type: 'SET_AUTHENTICATED'; payload: boolean }
  | { type: 'SET_PLATFORMS'; payload: Platform[] }
  | { type: 'SET_PAGE'; payload: string }
  | { type: 'SET_DOWNLOAD_JOBS'; payload: DownloadJob[] }
  | { type: 'ADD_DOWNLOAD_JOB'; payload: DownloadJob }
  | { type: 'UPDATE_DOWNLOAD_JOB'; payload: { id: string; updates: Partial<DownloadJob> } }
  | { type: 'SET_RECENT_CONTENT'; payload: Content[] }
  | { type: 'ADD_CONTENT'; payload: Content }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'CLEAR_ERROR' };

// Initial state
const initialState: AppState = {
  user: null,
  isAuthenticated: false,
  selectedPlatforms: [],
  currentPage: 'dashboard',
  downloadJobs: [],
  recentContent: [],
  isLoading: false,
  error: null,
};

// Reducer function
function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_USER':
      return {
        ...state,
        user: action.payload,
        isAuthenticated: action.payload !== null,
      };

    case 'SET_AUTHENTICATED':
      return {
        ...state,
        isAuthenticated: action.payload,
      };

    case 'SET_PLATFORMS':
      return {
        ...state,
        selectedPlatforms: action.payload,
      };

    case 'SET_PAGE':
      return {
        ...state,
        currentPage: action.payload,
      };

    case 'SET_DOWNLOAD_JOBS':
      return {
        ...state,
        downloadJobs: action.payload,
      };

    case 'ADD_DOWNLOAD_JOB':
      return {
        ...state,
        downloadJobs: [action.payload, ...state.downloadJobs],
      };

    case 'UPDATE_DOWNLOAD_JOB':
      return {
        ...state,
        downloadJobs: state.downloadJobs.map(job =>
          job.id === action.payload.id 
            ? { ...job, ...action.payload.updates }
            : job
        ),
      };

    case 'SET_RECENT_CONTENT':
      return {
        ...state,
        recentContent: action.payload,
      };

    case 'ADD_CONTENT':
      return {
        ...state,
        recentContent: [action.payload, ...state.recentContent.slice(0, 9)], // Keep last 10
      };

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };

    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
        isLoading: false,
      };

    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };

    default:
      return state;
  }
}

// Context interface
interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  // Helper functions
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
  addDownloadJob: (job: DownloadJob) => void;
  updateDownloadJob: (id: string, updates: Partial<DownloadJob>) => void;
  addContent: (content: Content) => void;
}

// Create context
const AppContext = createContext<AppContextType | undefined>(undefined);

// Provider component
interface AppProviderProps {
  children: ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Helper functions
  const setUser = (user: User | null) => {
    dispatch({ type: 'SET_USER', payload: user });
  };

  const setLoading = (loading: boolean) => {
    dispatch({ type: 'SET_LOADING', payload: loading });
  };

  const setError = (error: string | null) => {
    dispatch({ type: 'SET_ERROR', payload: error });
  };

  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  const addDownloadJob = (job: DownloadJob) => {
    dispatch({ type: 'ADD_DOWNLOAD_JOB', payload: job });
  };

  const updateDownloadJob = (id: string, updates: Partial<DownloadJob>) => {
    dispatch({ type: 'UPDATE_DOWNLOAD_JOB', payload: { id, updates } });
  };

  const addContent = (content: Content) => {
    dispatch({ type: 'ADD_CONTENT', payload: content });
  };

  const contextValue: AppContextType = {
    state,
    dispatch,
    setUser,
    setLoading,
    setError,
    clearError,
    addDownloadJob,
    updateDownloadJob,
    addContent,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
}

// Hook to use the context
export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}

export default AppContext; 