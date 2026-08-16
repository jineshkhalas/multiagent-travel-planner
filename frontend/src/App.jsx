import { useState, useEffect, useRef } from 'react';
import { auth, googleProvider, db } from './firebase';
import { 
  signInWithPopup, 
  signInWithRedirect, 
  getRedirectResult, 
  signOut, 
  onAuthStateChanged 
} from 'firebase/auth';
import { 
  collection, 
  addDoc, 
  doc, 
  updateDoc, 
  deleteDoc, 
  query, 
  where, 
  getDocs, 
  serverTimestamp 
} from 'firebase/firestore';
import ItineraryDisplay from './components/ItineraryDisplay';
import { 
  LogOut, 
  Plus, 
  ArrowLeft, 
  User, 
  MapPin, 
  Send, 
  Loader2, 
  Sparkles, 
  Trash2, 
  Copy, 
  Check, 
  Compass, 
  Plane, 
  CloudSun, 
  Building,
  BookmarkPlus,
  BookmarkCheck,
  Bookmark,
  X,
  Clock,
  Sun,
  Moon,
  MessageSquare
} from 'lucide-react';

const QUICK_PROMPTS = [
  "Plan a 3 day trip to Mumbai from Ahmedabad",
  "Plan it for 5 days by adding Lonavala",
  "Plan a 4 day budget trip to Goa from Pune"
];

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export default function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('login');
  const [activeTripId, setActiveTripId] = useState(null);
  const [activeTripTitle, setActiveTripTitle] = useState("New Trip Plan");
  const [chatHistory, setChatHistory] = useState([]);
  
  const [savedPlans, setSavedPlans] = useState([]);
  const [selectedPlanId, setSelectedPlanId] = useState(null);
  const [mobileActiveTab, setMobileActiveTab] = useState('chat');

  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(false);
  const [trips, setTrips] = useState([]);
  const [copied, setCopied] = useState(false);
  
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('travel_planner_theme');
    if (saved) return saved === 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  const chatBottomRef = useRef(null);

  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add('dark');
      document.body.classList.add('dark');
      localStorage.setItem('travel_planner_theme', 'dark');
    } else {
      root.classList.remove('dark');
      document.body.classList.remove('dark');
      localStorage.setItem('travel_planner_theme', 'light');
    }
  }, [darkMode]);

  const toggleDarkMode = () => {
    setDarkMode(prev => !prev);
  };

  useEffect(() => {
    getRedirectResult(auth)
      .then((result) => {
        if (result?.user) {
          setUser(result.user);
          setCurrentView('dashboard');
          fetchTrips(result.user.uid);
        }
      })
      .catch((err) => {
        if (err.code !== 'auth/credential-already-in-use') {
          console.warn("Auth redirect info:", err.message);
        }
      });

    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        setCurrentView((prev) => (prev === 'login' ? 'dashboard' : prev));
        fetchTrips(currentUser.uid);
      } else {
        setCurrentView('login');
        setTrips([]);
      }
    });
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isLoading]);

  const fetchTrips = async (userId) => {
    try {
      const q = query(collection(db, "trips"), where("userId", "==", userId));
      const querySnapshot = await getDocs(q);
      const tripsData = querySnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));

      // Sort newest first so the most recent plan is on the left beside 'Plan New Trip'
      tripsData.sort((a, b) => {
        const getTimestamp = (t) => {
          if (!t) return 0;
          if (t.updatedAt?.toMillis) return t.updatedAt.toMillis();
          if (t.updatedAt?.seconds) return t.updatedAt.seconds * 1000;
          if (t.createdAt?.toMillis) return t.createdAt.toMillis();
          if (t.createdAt?.seconds) return t.createdAt.seconds * 1000;
          if (typeof t.updatedAt === 'string') return new Date(t.updatedAt).getTime();
          if (typeof t.createdAt === 'string') return new Date(t.createdAt).getTime();
          return 0;
        };
        return getTimestamp(b) - getTimestamp(a);
      });

      setTrips(tripsData);
    } catch (error) {
      console.error("Error fetching trips:", error);
    }
  };

  const handleLogin = async () => {
    if (isLoggingIn) return;
    setIsLoggingIn(true);

    try {
      await signInWithPopup(auth, googleProvider);
    } catch (error) {
      if (
        error.code === 'auth/cancelled-popup-request' || 
        error.code === 'auth/popup-closed-by-user'
      ) {
        return;
      }
      
      if (error.code === 'auth/popup-blocked') {
        try {
          await signInWithRedirect(auth, googleProvider);
        } catch (redirectErr) {
          console.error("Redirect sign-in error:", redirectErr);
        }
      } else {
        console.error("Sign-in issue:", error.message || error);
      }
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = async () => {
    try {
      await signOut(auth);
      setUser(null);
      setCurrentView('login');
      setTrips([]);
      setChatHistory([]);
      setSavedPlans([]);
      setSelectedPlanId(null);
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  const createNewTrip = async () => {
    if (!user) return;
    try {
      const docRef = await addDoc(collection(db, "trips"), {
        userId: user.uid,
        title: "New Trip Plan",
        chatHistory: [],
        savedPlans: [],
        savedPlan: "",
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp()
      });
      setActiveTripId(docRef.id);
      setActiveTripTitle("New Trip Plan");
      setChatHistory([]);
      setSavedPlans([]);
      setSelectedPlanId(null);
      setMobileActiveTab('chat');
      setCurrentView('workspace');
      fetchTrips(user.uid);
    } catch (error) {
      console.error("Error creating new trip:", error);
    }
  };

  const openTrip = (trip) => {
    setActiveTripId(trip.id);
    setActiveTripTitle(trip.title || "Trip Plan");
    setChatHistory(trip.chatHistory || []);
    
    let plans = Array.isArray(trip.savedPlans) ? trip.savedPlans : [];
    if (plans.length === 0 && trip.savedPlan && typeof trip.savedPlan === 'string') {
      plans = [{
        id: 'plan_initial',
        title: trip.title || 'Saved Itinerary',
        content: trip.savedPlan,
        savedAt: new Date().toISOString()
      }];
    }

    setSavedPlans(plans);
    setSelectedPlanId(plans.length > 0 ? plans[0].id : null);
    setMobileActiveTab('chat');
    setCurrentView('workspace');
  };

  const handleDeleteTrip = async (e, tripId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this trip?")) return;
    try {
      await deleteDoc(doc(db, "trips", tripId));
      fetchTrips(user.uid);
      if (activeTripId === tripId) {
        setCurrentView('dashboard');
        setActiveTripId(null);
      }
    } catch (err) {
      console.error("Error deleting trip:", err);
    }
  };

  const handleSavePlan = async (msg) => {
    const alreadySaved = savedPlans.some(p => p.content === msg.content);
    if (alreadySaved) return;

    const title = msg.destination && msg.destination !== "Unknown"
      ? `${msg.duration_days ? msg.duration_days + '-Day ' : ''}Trip to ${msg.destination}`
      : `Travel Plan #${savedPlans.length + 1}`;

    const newPlanItem = {
      id: `plan_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      title: title,
      content: msg.content,
      source: msg.source,
      destination: msg.destination,
      duration_days: msg.duration_days,
      savedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ', ' + new Date().toLocaleDateString([], { month: 'short', day: 'numeric' })
    };

    const updatedPlans = [newPlanItem, ...savedPlans];
    setSavedPlans(updatedPlans);
    setSelectedPlanId(newPlanItem.id);

    if (activeTripId) {
      await updateDoc(doc(db, "trips", activeTripId), {
        savedPlans: updatedPlans,
        savedPlan: newPlanItem.content,
        updatedAt: serverTimestamp()
      });
      fetchTrips(user.uid);
    }
  };

  const handleDeleteSavedPlan = async (e, planId) => {
    e.stopPropagation();
    const updated = savedPlans.filter(p => p.id !== planId);
    setSavedPlans(updated);
    if (selectedPlanId === planId) {
      setSelectedPlanId(updated.length > 0 ? updated[0].id : null);
    }
    if (activeTripId) {
      await updateDoc(doc(db, "trips", activeTripId), {
        savedPlans: updated,
        savedPlan: updated.length > 0 ? updated[0].content : "",
        updatedAt: serverTimestamp()
      });
      fetchTrips(user.uid);
    }
  };

  const handleSendMessage = async (customMessage = null) => {
    const text = (customMessage || inputMessage).trim();
    if (!text || isLoading) return;

    setInputMessage("");
    const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString() };
    const updatedHistory = [...chatHistory, userMsg];
    setChatHistory(updatedHistory);
    setIsLoading(true);

    const currentActivePlan = savedPlans.find(p => p.id === selectedPlanId)?.content || "";

    try {
      const response = await fetch(`${API_BASE_URL}/api/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: text, 
          tripId: activeTripId,
          history: updatedHistory,
          currentPlan: currentActivePlan
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const data = await response.json();
      const planText = data.itinerary || data.reply || "";
      if (!planText || planText.trim().length < 30) {
        throw new Error("Unable to synthesize itinerary. Please try sending your request again.");
      }
      
      const assistantMsg = { 
        id: `msg_${Date.now()}`,
        role: 'assistant', 
        content: planText, 
        timestamp: new Date().toISOString(),
        source: data.source,
        destination: data.destination,
        duration_days: data.duration_days,
        isItinerary: true
      };

      const newHistory = [...updatedHistory, assistantMsg];
      setChatHistory(newHistory);

      let newTitle = activeTripTitle;
      if ((activeTripTitle === "New Trip Plan" || !activeTripTitle) && data.destination && data.destination !== "Unknown") {
        newTitle = `Trip to ${data.destination}`;
        setActiveTripTitle(newTitle);
      }

      if (activeTripId) {
        await updateDoc(doc(db, "trips", activeTripId), {
          chatHistory: newHistory,
          title: newTitle,
          updatedAt: serverTimestamp()
        });
        fetchTrips(user.uid);
      }
    } catch (err) {
      console.error("Failed to fetch plan:", err);
      const errorMsg = { 
        role: 'assistant', 
        content: `⚠️ **Agent Connection Error**: Could not connect to the Backend API at \`${API_BASE_URL}\`.\n\nMake sure the backend is started and reachable.`, 
        timestamp: new Date().toISOString(),
        isError: true 
      };
      setChatHistory([...updatedHistory, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const selectedPlan = savedPlans.find(p => p.id === selectedPlanId) || (savedPlans.length > 0 ? savedPlans[0] : null);

  const handleCopyPlan = () => {
    if (!selectedPlan?.content) return;
    navigator.clipboard.writeText(selectedPlan.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (currentView === 'login') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-blue-50 to-white dark:from-gray-950 dark:to-gray-900 px-3 sm:px-4 py-8 transition-colors duration-200 relative overflow-hidden">
        <div className="absolute top-3 right-3 sm:top-6 sm:right-6">
          <button
            onClick={toggleDarkMode}
            className="p-2 sm:p-2.5 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 transition cursor-pointer"
            title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {darkMode ? <Sun className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" /> : <Moon className="w-4 h-4 sm:w-5 sm:h-5 text-gray-600" />}
          </button>
        </div>

        <div className="bg-white dark:bg-gray-900 p-5 sm:p-8 md:p-10 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-800 flex flex-col items-center w-full max-w-[95%] sm:max-w-md text-center transition-colors">
          <div className="w-12 h-12 sm:w-16 sm:h-16 bg-blue-600 rounded-2xl flex items-center justify-center text-white mb-4 sm:mb-6 shadow-lg shadow-blue-500/30">
            <Compass className="w-7 h-7 sm:w-9 sm:h-9" />
          </div>
          <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">AI Travel Planner</h1>
          <p className="text-gray-500 dark:text-gray-400 mb-6 sm:mb-8 text-xs sm:text-sm leading-relaxed">
            Multi-Agent A2A collaborative engine for real-time flights, live weather, hotels, and custom itineraries.
          </p>
          <button 
            onClick={handleLogin} 
            disabled={isLoggingIn}
            className="w-full bg-blue-600 hover:bg-blue-700 active:scale-95 text-white font-semibold py-3 sm:py-3.5 px-4 sm:px-6 rounded-xl shadow-md transition flex items-center justify-center gap-2.5 text-xs sm:text-sm cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isLoggingIn ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                <span>Signing in...</span>
              </>
            ) : (
              <>
                <MapPin className="w-4 h-4 sm:w-5 sm:h-5 shrink-0" />
                <span>Sign in with Google</span>
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  if (currentView === 'dashboard') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col transition-colors duration-200">
        <div className="flex-1 p-3 sm:p-6 md:p-8 max-w-7xl w-full mx-auto">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-4 mb-6 sm:mb-8">
            <div className="min-w-0">
              <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900 dark:text-gray-100 truncate">My Travel Plans</h1>
              <p className="text-gray-500 dark:text-gray-400 text-xs sm:text-sm mt-0.5 sm:mt-1">Manage and create your multi-agent itineraries</p>
            </div>
            <div className="flex items-center flex-wrap gap-2 sm:gap-3 shrink-0">
              <button
                onClick={toggleDarkMode}
                className="p-2 sm:p-2.5 rounded-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 transition cursor-pointer"
                title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
              >
                {darkMode ? <Sun className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" /> : <Moon className="w-4 h-4 sm:w-5 sm:h-5 text-gray-600" />}
              </button>

              <button 
                onClick={() => setRightSidebarOpen(!rightSidebarOpen)} 
                className="p-2 sm:p-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-full shadow-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition cursor-pointer"
                title="Account profile"
              >
                <User className="text-gray-700 dark:text-gray-300 w-4 h-4 sm:w-5 sm:h-5" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
            <div
              onClick={createNewTrip}
              className="min-h-[170px] sm:min-h-[200px] border-2 border-dashed border-blue-300 dark:border-blue-800/80 bg-blue-50/40 dark:bg-blue-950/20 rounded-2xl flex flex-col items-center justify-center cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-950/40 hover:border-blue-500 transition group p-4 sm:p-6 text-center"
            >
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-blue-100 dark:bg-blue-900/60 flex items-center justify-center text-blue-600 dark:text-blue-400 mb-2 sm:mb-3 group-hover:scale-110 transition">
                <Plus className="w-5 h-5 sm:w-6 sm:h-6" />
              </div>
              <span className="text-gray-800 dark:text-gray-200 font-semibold text-sm sm:text-base group-hover:text-blue-600 dark:group-hover:text-blue-400 transition">Plan New Trip</span>
              <span className="text-[11px] sm:text-xs text-gray-400 dark:text-gray-500 mt-0.5 sm:mt-1">Invoke collaborative A2A agents</span>
            </div>

            {trips.map(trip => {
              const plansCount = Array.isArray(trip.savedPlans) ? trip.savedPlans.length : (trip.savedPlan ? 1 : 0);
              return (
                <div
                  key={trip.id}
                  onClick={() => openTrip(trip)}
                  className="min-h-[170px] sm:min-h-[200px] bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-4 sm:p-6 cursor-pointer hover:shadow-md hover:border-blue-400 dark:hover:border-blue-600 transition flex flex-col justify-between group relative"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2 sm:mb-3">
                      <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                        <MapPin className="w-4 h-4 sm:w-5 sm:h-5" />
                      </div>
                      <button
                        onClick={(e) => handleDeleteTrip(e, trip.id)}
                        className="text-gray-400 hover:text-red-600 p-1 rounded-md transition cursor-pointer"
                        title="Delete trip"
                      >
                        <Trash2 className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                      </button>
                    </div>
                    <h3 className="text-sm sm:text-base md:text-lg font-bold text-gray-800 dark:text-gray-100 line-clamp-2">{trip.title || "Untitled Trip"}</h3>
                  </div>

                  <div className="pt-3 sm:pt-4 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between text-[11px] sm:text-xs text-gray-400 dark:text-gray-500">
                    <span className="flex items-center gap-1 font-medium text-gray-600 dark:text-gray-400 truncate">
                      <Bookmark className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                      <span>{plansCount > 0 ? `${plansCount} Saved Plan${plansCount > 1 ? 's' : ''}` : "In Progress"}</span>
                    </span>
                    <span className="text-blue-600 dark:text-blue-400 font-medium group-hover:translate-x-1 transition shrink-0 ml-1">Open &rarr;</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {rightSidebarOpen && user && (
          <div className="fixed inset-0 z-50 flex justify-end">
            <div 
              className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity"
              onClick={() => setRightSidebarOpen(false)}
            />
            <div className="relative w-full sm:w-80 max-w-[85vw] bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 p-5 sm:p-6 shadow-2xl flex flex-col justify-between z-10 transition-colors">
              <div>
                <div className="flex justify-between items-center pb-3 border-b border-gray-100 dark:border-gray-800">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Account</span>
                  <button 
                    onClick={() => setRightSidebarOpen(false)}
                    className="p-1 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex flex-col items-center text-center mt-6">
                  {user.photoURL ? (
                    <img src={user.photoURL} className="w-16 h-16 sm:w-20 sm:h-20 rounded-full mb-3 object-cover border-2 border-blue-500 shadow-sm" alt="Profile" />
                  ) : (
                    <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full mb-3 bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center border border-blue-200 dark:border-blue-800">
                      <User className="w-8 h-8 sm:w-10 sm:h-10" />
                    </div>
                  )}
                  <h2 className="text-base sm:text-lg font-bold text-gray-900 dark:text-gray-100 truncate w-full">{user.displayName || 'Traveler'}</h2>
                  <p className="text-gray-500 dark:text-gray-400 text-xs sm:text-sm mb-6 truncate w-full">{user.email}</p>
                </div>
              </div>

              <button 
                onClick={handleLogout} 
                className="flex items-center justify-center gap-2 text-red-600 font-medium hover:bg-red-50 dark:hover:bg-red-950/40 py-2.5 sm:py-3 rounded-xl border border-red-200 dark:border-red-900/60 text-xs sm:text-sm transition cursor-pointer"
              >
                <LogOut className="w-4 h-4 sm:w-5 sm:h-5" /> Sign Out
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  if (currentView === 'workspace') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col h-screen overflow-hidden transition-colors duration-200">
        <div className="h-14 sm:h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 flex items-center px-2.5 sm:px-4 md:px-6 justify-between shrink-0 transition-colors gap-2">
          <div className="flex items-center gap-2 sm:gap-4 min-w-0">
            <button 
              onClick={() => { setCurrentView('dashboard'); fetchTrips(user.uid); }} 
              className="flex items-center gap-1 sm:gap-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition font-medium text-xs sm:text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 px-2 sm:px-3 py-1.5 rounded-lg cursor-pointer shrink-0"
            >
              <ArrowLeft className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span className="hidden sm:inline">Back</span>
            </button>
            <div className="h-4 sm:h-5 w-px bg-gray-300 dark:bg-gray-700 shrink-0"></div>
            <div className="flex items-center gap-1.5 min-w-0">
              <Compass className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600 dark:text-blue-400 shrink-0" />
              <span className="font-bold text-gray-800 dark:text-gray-100 text-xs sm:text-sm md:text-base truncate max-w-[120px] xs:max-w-[180px] sm:max-w-xs md:max-w-md">{activeTripTitle}</span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
            <div className="flex lg:hidden bg-gray-100 dark:bg-gray-800 p-0.5 rounded-lg border border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setMobileActiveTab('chat')}
                className={`flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-semibold transition cursor-pointer ${
                  mobileActiveTab === 'chat'
                    ? 'bg-white dark:bg-gray-900 text-blue-600 dark:text-blue-400 shadow-xs'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                }`}
              >
                <MessageSquare className="w-3 h-3" />
                <span>Chat</span>
              </button>
              <button
                onClick={() => setMobileActiveTab('saved_plans')}
                className={`flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-semibold transition cursor-pointer ${
                  mobileActiveTab === 'saved_plans'
                    ? 'bg-white dark:bg-gray-900 text-blue-600 dark:text-blue-400 shadow-xs'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                }`}
              >
                <Bookmark className="w-3 h-3" />
                <span>Saved Plans {savedPlans.length > 0 && `(${savedPlans.length})`}</span>
              </button>
            </div>

            <button
              onClick={toggleDarkMode}
              className="p-1.5 sm:p-2 rounded-full bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition cursor-pointer shrink-0"
              title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {darkMode ? <Sun className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-amber-400" /> : <Moon className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-600" />}
            </button>
          </div>
        </div>

        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0">
          <div className={`flex-1 flex-col bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transition-colors min-h-0 ${
            mobileActiveTab === 'chat' ? 'flex' : 'hidden lg:flex'
          }`}>
            <div className="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6 bg-gray-50/70 dark:bg-gray-950/70 space-y-3 sm:space-y-4">
              <div className="bg-white dark:bg-gray-900 border border-blue-100 dark:border-gray-800 rounded-2xl p-4 sm:p-5 shadow-sm max-w-2xl">
                <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 font-semibold mb-2 text-sm sm:text-base">
                  <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 shrink-0" />
                  <span>AI Multi-Agent Travel Planner</span>
                </div>
                <p className="text-gray-600 dark:text-gray-300 text-xs sm:text-sm leading-relaxed mb-3 sm:mb-4">
                  Where would you like to travel? Enter your starting point, destination, and duration. 
                  Our specialist agents (Weather, Flights, Hotels, and Attractions) will collaborate to build your custom plan.
                </p>

                {chatHistory.length === 0 && (
                  <div className="space-y-2 pt-2 border-t border-gray-100 dark:border-gray-800">
                    <p className="text-[10px] sm:text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">Try quick prompts:</p>
                    <div className="flex flex-wrap gap-1.5 sm:gap-2">
                      {QUICK_PROMPTS.map((prompt, i) => (
                        <button
                          key={i}
                          onClick={() => handleSendMessage(prompt)}
                          className="text-[11px] sm:text-xs bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/60 px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-lg font-medium transition cursor-pointer border border-blue-200 dark:border-blue-800/80 break-words text-left"
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {chatHistory.map((msg, idx) => {
                const isSaved = savedPlans.some(p => p.content === msg.content);
                const isAssistantPlan = msg.role === 'assistant' && !msg.isError;

                return (
                  <div 
                    key={idx} 
                    className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                  >
                    <div 
                      className={`max-w-[95%] sm:max-w-[88%] rounded-2xl p-3 sm:p-5 shadow-sm text-xs sm:text-sm break-words overflow-hidden ${
                        msg.role === 'user' 
                          ? 'bg-blue-600 text-white rounded-tr-none' 
                          : msg.isError 
                            ? 'bg-red-50 dark:bg-red-950/40 text-red-900 dark:text-red-200 border border-red-200 dark:border-red-900/60 rounded-tl-none'
                            : 'bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100 border border-gray-200 dark:border-gray-800 rounded-tl-none'
                      }`}
                    >
                      {msg.role === 'user' ? (
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      ) : (
                        <div>
                          <ItineraryDisplay content={msg.content} />

                          {isAssistantPlan && (
                            <div className="mt-3 sm:mt-4 pt-2.5 sm:pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between flex-wrap gap-2">
                              <span className="text-[10px] sm:text-xs text-gray-400 dark:text-gray-500 font-medium flex items-center gap-1.5">
                                <Sparkles className="w-3.5 h-3.5 text-blue-500 shrink-0" /> Multi-Agent Itinerary
                              </span>
                              <button
                                onClick={() => {
                                  handleSavePlan(msg);
                                }}
                                disabled={isSaved}
                                className={`flex items-center gap-1.5 px-2.5 sm:px-3.5 py-1 sm:py-1.5 rounded-xl text-[11px] sm:text-xs font-semibold transition cursor-pointer shadow-sm ${
                                  isSaved
                                    ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/80'
                                    : 'bg-blue-600 hover:bg-blue-700 active:scale-95 text-white'
                                }`}
                              >
                                {isSaved ? (
                                  <>
                                    <BookmarkCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                                    <span>Saved to My Plans</span>
                                  </>
                                ) : (
                                  <>
                                    <BookmarkPlus className="w-3.5 h-3.5 shrink-0" />
                                    <span>Save This Plan</span>
                                  </>
                                )}
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    <span className="text-[10px] text-gray-400 dark:text-gray-500 mt-1 px-1">
                      {msg.role === 'user' ? 'You' : 'Planner AI'}
                    </span>
                  </div>
                );
              })}

              {isLoading && (
                <div className="flex items-start gap-2.5 sm:gap-3 bg-white dark:bg-gray-900 border border-blue-200 dark:border-gray-800 rounded-2xl p-3 sm:p-4 shadow-sm max-w-md animate-pulse">
                  <div className="p-1.5 sm:p-2 bg-blue-100 dark:bg-blue-900/50 rounded-xl text-blue-600 dark:text-blue-400 shrink-0">
                    <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
                  </div>
                  <div className="text-xs sm:text-sm">
                    <p className="font-semibold text-gray-900 dark:text-gray-100">Agents in Action...</p>
                    <div className="flex items-center flex-wrap gap-2 text-[10px] sm:text-xs text-gray-500 dark:text-gray-400 mt-1.5">
                      <span className="flex items-center gap-1"><CloudSun className="w-3 h-3 text-amber-500" /> Weather</span>
                      <span className="flex items-center gap-1"><Plane className="w-3 h-3 text-blue-500" /> Flights</span>
                      <span className="flex items-center gap-1"><Building className="w-3 h-3 text-emerald-500" /> Hotels</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={chatBottomRef} />
            </div>

            <div className="p-2.5 sm:p-4 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 shrink-0 transition-colors">
              <div className="max-w-4xl mx-auto flex gap-2 sm:gap-3">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="e.g., Plan a 4 day trip to Goa in budget ₹15,000..."
                  disabled={isLoading}
                  className="flex-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 rounded-xl px-3 sm:px-4 py-2.5 sm:py-3 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition disabled:bg-gray-100 dark:disabled:bg-gray-800"
                />
                <button 
                  onClick={() => handleSendMessage()}
                  disabled={isLoading || !inputMessage.trim()}
                  className="bg-blue-600 text-white px-3.5 sm:px-5 py-2.5 sm:py-3 rounded-xl font-medium hover:bg-blue-700 transition shadow-sm flex items-center justify-center gap-1.5 text-xs sm:text-sm cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
                >
                  {isLoading ? <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin" /> : <Send className="w-3.5 h-3.5 sm:w-4 sm:h-4" />}
                  <span className="hidden xs:inline sm:inline">Send</span>
                </button>
              </div>
            </div>
          </div>

          <div className={`w-full lg:w-1/2 bg-white dark:bg-gray-900 flex-col shadow-[-4px_0_15px_-3px_rgba(0,0,0,0.03)] shrink-0 transition-colors min-h-0 ${
            mobileActiveTab === 'saved_plans' ? 'flex' : 'hidden lg:flex'
          }`}>
            <div className="p-3 sm:p-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50/90 dark:bg-gray-900/90 flex justify-between items-center gap-2">
              <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
                <Bookmark className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
                <h2 className="font-bold text-gray-800 dark:text-gray-100 text-xs sm:text-sm truncate">Saved Plans</h2>
                <span className="text-[10px] sm:text-xs bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 font-semibold px-2 py-0.5 rounded-full border border-blue-200 dark:border-blue-800/60 shrink-0">
                  {savedPlans.length} {savedPlans.length === 1 ? 'Plan' : 'Plans'}
                </span>
              </div>

              {selectedPlan && (
                <button
                  onClick={handleCopyPlan}
                  className="flex items-center gap-1.5 text-[11px] sm:text-xs font-medium text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-blue-300 px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-lg shadow-sm transition cursor-pointer shrink-0"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-green-600 dark:text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? "Copied!" : "Copy Plan"}</span>
                </button>
              )}
            </div>

            {savedPlans.length > 0 && (
              <div className="flex gap-1.5 sm:gap-2 overflow-x-auto p-2 sm:p-3 bg-gray-100/60 dark:bg-gray-950/80 border-b border-gray-200 dark:border-gray-800 scrollbar-thin">
                {savedPlans.map((plan, idx) => {
                  const isSelected = plan.id === selectedPlanId || (!selectedPlanId && idx === 0);
                  return (
                    <div
                      key={plan.id}
                      onClick={() => setSelectedPlanId(plan.id)}
                      className={`flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1.5 sm:py-2 rounded-xl text-[11px] sm:text-xs font-semibold shrink-0 transition border cursor-pointer group ${
                        isSelected
                          ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                          : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800'
                      }`}
                    >
                      <Bookmark className="w-3 h-3 sm:w-3.5 sm:h-3.5 shrink-0" />
                      <span className="max-w-[110px] sm:max-w-[150px] truncate">{plan.title}</span>
                      <button
                        onClick={(e) => handleDeleteSavedPlan(e, plan.id)}
                        className={`p-0.5 rounded-full hover:bg-black/10 transition ${isSelected ? 'text-white/80 hover:text-white' : 'text-gray-400 hover:text-red-500'}`}
                        title="Remove saved plan"
                      >
                        <X className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="flex-1 p-3 sm:p-6 overflow-y-auto bg-white dark:bg-gray-900">
              {selectedPlan ? (
                <div>
                  <div className="mb-3 sm:mb-4 pb-2 sm:pb-3 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between text-[11px] sm:text-xs text-gray-400 dark:text-gray-500 flex-wrap gap-1">
                    <span className="font-semibold text-gray-700 dark:text-gray-200 text-xs sm:text-sm truncate">{selectedPlan.title}</span>
                    {selectedPlan.savedAt && (
                      <span className="flex items-center gap-1 shrink-0">
                        <Clock className="w-3 h-3" /> {selectedPlan.savedAt}
                      </span>
                    )}
                  </div>
                  <ItineraryDisplay content={selectedPlan.content} />
                </div>
              ) : (
                <div className="border-2 border-dashed border-gray-200 dark:border-gray-800 rounded-2xl p-6 sm:p-10 text-center h-full flex flex-col items-center justify-center text-gray-400 dark:text-gray-500">
                  <div className="w-12 h-12 sm:w-14 sm:h-14 bg-blue-50 dark:bg-blue-950/60 rounded-full flex items-center justify-center text-blue-500 dark:text-blue-400 mb-3 shadow-inner">
                    <BookmarkPlus className="w-6 h-6 sm:w-7 sm:h-7" />
                  </div>
                  <h4 className="font-semibold text-gray-700 dark:text-gray-300 mb-1 text-sm sm:text-base">No Saved Plans Yet</h4>
                  <p className="text-[11px] sm:text-xs max-w-sm leading-relaxed mb-4">
                    When the AI creates an itinerary you like in the chat, click <strong>"Save This Plan"</strong> to store and compare different trip options here.
                  </p>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    );
  }

}