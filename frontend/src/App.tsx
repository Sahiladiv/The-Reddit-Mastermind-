import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Home from "./pages/Home";
import SubredditPosts from "./components/SubredditPosts";
import PostView from "./components/PostView";
import "./styles.css";

export default function App() {
  return (
    <Router>
      <div className="layout">
        <Sidebar />

        <div className="main">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/r/:subreddit" element={<SubredditPosts />} />
            <Route path="/post/:id" element={<PostView />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}
