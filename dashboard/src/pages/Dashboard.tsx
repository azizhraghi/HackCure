import { Link } from 'react-router-dom';
import { Search, FileText, AlertTriangle, CheckCircle2, Clock } from 'lucide-react';

const patients = [
  {
    id: "pt_demo_001",
    name: "Sarah Miller",
    surgery: "Right Total Knee Replacement (TKA)",
    date: "2025-06-04",
    status: "Draft",
    alert: "High Pain (EVA 8)",
  },
  {
    id: "pt_002",
    name: "Marcus Johnson",
    surgery: "ACL Reconstruction",
    date: "2025-06-05",
    status: "Active",
    alert: null,
  },
  {
    id: "pt_003",
    name: "Emma Davis",
    surgery: "Hip Replacement",
    date: "2025-06-06",
    status: "In Review",
    alert: null,
  }
];

export default function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Top Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4 transform transition-all hover:scale-105 hover:shadow-md cursor-pointer">
          <div className="p-3 bg-blue-100 text-blue-600 rounded-xl"><FileText className="w-6 h-6" /></div>
          <div>
            <p className="text-sm text-gray-500 font-medium">Pending Protocols</p>
            <p className="text-2xl font-bold text-gray-900">4</p>
          </div>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4 transform transition-all hover:scale-105 hover:shadow-md cursor-pointer">
          <div className="p-3 bg-red-100 text-red-600 rounded-xl"><AlertTriangle className="w-6 h-6" /></div>
          <div>
            <p className="text-sm text-gray-500 font-medium">Active Alerts</p>
            <p className="text-2xl font-bold text-gray-900">2</p>
          </div>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4 transform transition-all hover:scale-105 hover:shadow-md cursor-pointer">
          <div className="p-3 bg-green-100 text-green-600 rounded-xl"><CheckCircle2 className="w-6 h-6" /></div>
          <div>
            <p className="text-sm text-gray-500 font-medium">Cleared Today</p>
            <p className="text-2xl font-bold text-gray-900">12</p>
          </div>
        </div>
      </div>

      {/* Patient List */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-lg font-bold text-gray-900">Recent Patients</h3>
          <div className="relative">
            <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input 
              type="text" 
              placeholder="Search patients..." 
              className="pl-10 pr-4 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
            />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50/50">
                <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Patient Name</th>
                <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Surgery</th>
                <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
                <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Protocol Status</th>
                <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Alerts</th>
                <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {patients.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50/50 transition-colors group">
                  <td className="py-4 px-6">
                    <div className="flex items-center">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 text-indigo-700 flex items-center justify-center font-bold text-xs mr-3">
                        {p.name.split(' ').map(n=>n[0]).join('')}
                      </div>
                      <span className="font-semibold text-gray-900">{p.name}</span>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-sm text-gray-600">{p.surgery}</td>
                  <td className="py-4 px-6 text-sm text-gray-500 flex items-center">
                    <Clock className="w-4 h-4 mr-2 text-gray-400" />
                    {p.date}
                  </td>
                  <td className="py-4 px-6">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${
                      p.status === 'Draft' ? 'bg-yellow-50 text-yellow-700 border-yellow-200' :
                      p.status === 'Active' ? 'bg-green-50 text-green-700 border-green-200' :
                      'bg-blue-50 text-blue-700 border-blue-200'
                    }`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    {p.alert ? (
                      <span className="inline-flex items-center text-sm font-medium text-red-600">
                        <AlertTriangle className="w-4 h-4 mr-1.5" />
                        {p.alert}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-sm">-</span>
                    )}
                  </td>
                  <td className="py-4 px-6">
                    <Link to={`/protocol/${p.id}`} className="text-sm font-semibold text-blue-600 hover:text-blue-800 transition-colors">
                      Review &rarr;
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
