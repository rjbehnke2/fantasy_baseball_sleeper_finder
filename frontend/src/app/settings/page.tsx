"use client";

import { useState } from "react";

export default function SettingsPage() {
  const [leagueName, setLeagueName] = useState("My Dynasty League");
  const [format, setFormat] = useState("dynasty");
  const [scoringType, setScoringType] = useState("roto");
  const [budget, setBudget] = useState(260);
  const [rosterSize, setRosterSize] = useState(24);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    // TODO: POST to API when backend league settings are connected
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">League Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Configure your league format to personalize rankings and valuations.
        </p>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6 max-w-2xl">
        <div className="space-y-5">
          {/* League Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">League Name</label>
            <input
              type="text"
              value={leagueName}
              onChange={(e) => setLeagueName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* League Format */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">League Format</label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="dynasty">Dynasty</option>
              <option value="keeper">Keeper</option>
              <option value="redraft">Redraft</option>
            </select>
          </div>

          {/* Scoring Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Scoring Type</label>
            <select
              value={scoringType}
              onChange={(e) => setScoringType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="roto">Rotisserie (Roto)</option>
              <option value="h2h_categories">H2H Categories</option>
              <option value="h2h_points">H2H Points</option>
            </select>
          </div>

          {/* Auction Budget */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Auction Budget (per team)
            </label>
            <div className="flex items-center gap-2">
              <span className="text-gray-500">$</span>
              <input
                type="number"
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                className="w-32 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Roster Size */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Roster Size</label>
            <input
              type="number"
              value={rosterSize}
              onChange={(e) => setRosterSize(Number(e.target.value))}
              className="w-32 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Stat Categories */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Batting Categories</label>
            <div className="flex flex-wrap gap-2">
              {["HR", "RBI", "R", "SB", "AVG", "OBP", "SLG", "OPS"].map((cat) => (
                <label key={cat} className="flex items-center gap-1 text-sm">
                  <input
                    type="checkbox"
                    defaultChecked={["HR", "RBI", "R", "SB", "AVG"].includes(cat)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  {cat}
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Pitching Categories</label>
            <div className="flex flex-wrap gap-2">
              {["W", "SV", "SO", "ERA", "WHIP", "K/9", "QS", "HLD"].map((cat) => (
                <label key={cat} className="flex items-center gap-1 text-sm">
                  <input
                    type="checkbox"
                    defaultChecked={["W", "SV", "SO", "ERA", "WHIP"].includes(cat)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  {cat}
                </label>
              ))}
            </div>
          </div>

          {/* Save Button */}
          <div className="pt-2">
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
            >
              {saved ? "Saved!" : "Save Settings"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
