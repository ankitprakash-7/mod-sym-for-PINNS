const DataDashboard = () => {
      const Card = ({ title, value, change }) => (
        <div className="bg-gray-800/50 p-6 rounded-lg shadow-md backdrop-blur-sm">
          <h3 className="text-gray-400 text-sm font-medium">{title}</h3>
          <p className="text-white text-3xl font-bold my-2">{value}</p>
          <p className={`text-sm ${change.startsWith('+') ? 'text-green-400' : 'text-red-400'}`}>
            {change}
          </p>
        </div>
      );

      return (
        <div className="text-white">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card title="Active Users" value="1,492" change="+5.4% from last week" />
            <Card title="Revenue" value="$28,340" change="+12.1% from last week" />
            <Card title="Conversion Rate" value="3.8%" change="-0.2% from last week" />
            <Card title="Avg. Session" value="12m 45s" change="+1.5% from last week" />
          </div>
          <div className="mt-6 bg-gray-800/50 p-4 rounded-lg backdrop-blur-sm">
            <h3 className="font-semibold mb-4">User Activity (Last 7 Days)</h3>
            <div className="flex items-end h-48 bg-gray-900/50 p-4 rounded-md space-x-2">
                {[60, 80, 75, 90, 65, 85, 100].map((height, i) => (
                    <div key={i} className="flex-1 bg-green-500 rounded-t-sm hover:bg-green-400 transition-colors" style={{ height: `${height}%` }}></div>
                ))}
            </div>
          </div>
        </div>
      );
    };

    export default DataDashboard;
