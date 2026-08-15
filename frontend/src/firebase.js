import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
    apiKey: "AIzaSyC923p-FmBtAe6frNm4ck-7kcAIlvP4ZIU",
    authDomain: "travel-planner-a2a.firebaseapp.com",
    projectId: "travel-planner-a2a",
    storageBucket: "travel-planner-a2a.firebasestorage.app",
    messagingSenderId: "385921077462",
    appId: "1:385921077462:web:d3852dc9703b2bc75f7977",
    measurementId: "G-9W4PL0N98Y"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

export const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });

export const db = getFirestore(app);