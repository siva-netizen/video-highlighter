import { Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "./layout/Shell";
import { Landing } from "./pages/Landing";
import { Studio } from "./pages/Studio";

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Landing />} />
        <Route path="studio" element={<Studio />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
