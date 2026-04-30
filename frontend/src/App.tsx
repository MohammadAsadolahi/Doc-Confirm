import { Routes, Route } from "react-router-dom";
import { MainLayout } from "./components/layout/MainLayout";
import Dashboard from "./pages/Dashboard";
import DocumentInput from "./pages/DocumentInput";
import Verification from "./pages/Verification";
import Quiz from "./pages/Quiz";
import Report from "./pages/Report";

function App() {
    return (
        <MainLayout>
            <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/project/:id/input" element={<DocumentInput />} />
                <Route path="/project/:id/verify" element={<Verification />} />
                <Route path="/project/:id/quiz" element={<Quiz />} />
                <Route path="/project/:id/report" element={<Report />} />
            </Routes>
        </MainLayout>
    );
}

export default App;
