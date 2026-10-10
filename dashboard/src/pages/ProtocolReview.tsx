import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Check, FileCheck2, Bot, AlertCircle } from 'lucide-react';

export default function ProtocolReview() {
  const { patientId } = useParams();
  const [approved, setApproved] = useState(false);

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/" className="p-2 hover:bg-white rounded-full transition-colors text-gray-500">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Protocol Review: Sarah Miller</h1>
            <p className="text-sm text-gray-500">AI Extracted on June 4, 2025</p>
          </div>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-xl font-medium shadow-sm hover:bg-gray-50 transition-colors">
            Edit Manually
          </button>
          <button 
            onClick={() => setApproved(true)}
            disabled={approved}
            className={`px-4 py-2 rounded-xl font-medium shadow-sm flex items-center transition-all ${
              approved ? 'bg-green-100 text-green-700 cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {approved ? <><Check className="w-4 h-4 mr-2" /> Approved</> : <><FileCheck2 className="w-4 h-4 mr-2" /> Approve Protocol</>}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Original Documents */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 flex flex-col h-[700px]">
          <div className="p-4 border-b border-gray-100 bg-gray-50/50 rounded-t-2xl flex justify-between items-center">
            <h3 className="font-semibold text-gray-700 flex items-center">
              Original Document
            </h3>
            <select className="text-sm border-gray-200 rounded-lg bg-white">
              <option>Ordonnance_PostOp.pdf</option>
              <option>Compte_Rendu_Op.pdf</option>
            </select>
          </div>
          <div className="flex-1 p-6 overflow-y-auto font-mono text-sm text-gray-600 leading-relaxed bg-[#fbfbfb]">
            <p>DR. ELENA RUIZ<br/>ST JOSEPH MEDICAL CENTER</p>
            <p className="mt-4">Patient: Sarah Miller<br/>Date: 2025-06-04</p>
            <div className="mt-6 space-y-4">
              <p><strong>R/</strong></p>
              <p>1. Paracétamol (Doliprane) 1g<br/>- 3 fois par jour (matin, midi, soir)<br/>- 14 jours ou selon douleur<br/>- Ne pas dépasser 4g/jour</p>
              <p>2. Célécoxib (Celebrex) 200mg<br/>- 1 fois par jour le matin<br/>- 14 jours<br/>- Prendre au milieu du repas</p>
              <p>3. Pantoprazole (Inexium) 20mg<br/>- 1 fois par jour le matin à jeun<br/>- 14 jours</p>
              <p>4. Énoxaparine sodique (Lovenox) 4000 UI<br/>- 1 injection/jour le soir pendant 14 jours</p>
            </div>
          </div>
        </div>

        {/* Right: AI Extraction */}
        <div className="bg-white rounded-2xl shadow-sm border border-blue-100 flex flex-col h-[700px] relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-indigo-500"></div>
          <div className="p-4 border-b border-gray-100 flex justify-between items-center">
            <h3 className="font-semibold text-blue-900 flex items-center">
              <Bot className="w-5 h-5 mr-2 text-blue-600" />
              AI Structured Protocol
            </h3>
            <span className="px-2.5 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full">High Confidence</span>
          </div>
          <div className="flex-1 p-6 overflow-y-auto space-y-6">
            
            <div className="space-y-3">
              <h4 className="text-sm font-bold text-gray-400 uppercase tracking-wider">Medications</h4>
              
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 flex items-start group hover:border-blue-300 transition-colors">
                <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 mr-3"></div>
                <div>
                  <p className="font-bold text-gray-900">Paracétamol <span className="text-gray-500 font-normal">1 g</span></p>
                  <p className="text-sm text-gray-600 mt-1">3 fois par jour (matin, midi, soir) pendant 14 jours</p>
                  <p className="text-xs text-orange-600 mt-2 flex items-center bg-orange-50 px-2 py-1 rounded-md inline-flex">
                    <AlertCircle className="w-3 h-3 mr-1" /> Ne pas dépasser 4 g par jour
                  </p>
                </div>
              </div>

              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 flex items-start group hover:border-blue-300 transition-colors">
                <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 mr-3"></div>
                <div>
                  <p className="font-bold text-gray-900">Célécoxib <span className="text-gray-500 font-normal">200 mg</span></p>
                  <p className="text-sm text-gray-600 mt-1">1 fois par jour le matin pendant 14 jours</p>
                  <p className="text-xs text-gray-500 mt-2">Instruction: Prendre au milieu du repas</p>
                </div>
              </div>

              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 flex items-start group hover:border-blue-300 transition-colors">
                <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 mr-3"></div>
                <div>
                  <p className="font-bold text-gray-900">Pantoprazole <span className="text-gray-500 font-normal">20 mg</span></p>
                  <p className="text-sm text-gray-600 mt-1">1 fois par jour le matin pendant 14 jours</p>
                  <p className="text-xs text-gray-500 mt-2">Instruction: Prendre à jeun</p>
                </div>
              </div>

              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 flex items-start group hover:border-blue-300 transition-colors">
                <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 mr-3"></div>
                <div>
                  <p className="font-bold text-gray-900">Énoxaparine sodique <span className="text-gray-500 font-normal">4000 UI</span></p>
                  <p className="text-sm text-gray-600 mt-1">1 injection par jour le soir pendant 14 jours</p>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-100">
              <h4 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">AI Verification</h4>
              <div className="bg-green-50 text-green-700 p-3 rounded-xl text-sm flex items-start">
                <Check className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                <p>No dangerous drug interactions detected in extracted regimen.</p>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
