import "./api";
import React from "react";
import ReactDOM from "react-dom/client";
import AuthGate from "./AuthGate";
import "./index.css";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <AuthGate />
  </React.StrictMode>
);
