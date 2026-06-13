import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import ProfileForm from "./pages/ProfileForm";
import Universities from "./pages/Universities";
import Documents from "./pages/Documents";
import SopGenerator from "./pages/SopGenerator";
import MockInterview from "./pages/MockInterview";
import VisaGuidance from "./pages/VisaGuidance";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/profile" element={<ProfileForm />} />
          <Route path="/universities" element={<Universities />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/sop" element={<SopGenerator />} />
          <Route path="/interview" element={<MockInterview />} />
          <Route path="/visa" element={<VisaGuidance />} />
        </Route>
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}
