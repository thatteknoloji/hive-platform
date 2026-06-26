import "./api";
import React from "react";
import ReactDOM from "react-dom/client";
import AuthGate from "./AuthGate";
import { ActiveProjectProvider } from "./context/ActiveProjectContext";
import "./index.css";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <ActiveProjectProvider>
      <AuthGate />
    </ActiveProjectProvider>
  </React.StrictMode>
);
