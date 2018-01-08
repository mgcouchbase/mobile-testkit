using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Text;

using JetBrains.Annotations;

using Newtonsoft.Json;

namespace Couchbase.Lite.Testing
{
    public class ValueSerializer
    {
        public static string Serialize(Object value, Type t)
        {
            if (value == null)
            {
                return "null";
            }
            else if (t.Equals(typeof(string)))
            {
                return value.ToString();
            }
            else if (t.Equals(typeof(int)) || t.Equals(typeof(UInt64)))
            {
                return "I" + value;
            }
            else
            {
                return value.ToString();
            }

        }

        public static Dictionary<string, object> Deserialize(IReadOnlyDictionary<string, string> jsonObj)
        {
            Dictionary<string, object> bodyObj = new Dictionary<string, object>();

            foreach (string key in jsonObj.Keys)
            {
                string value = jsonObj[key];

                if (value == "null")
                {
                    bodyObj.Add(key, null);
                }
                else if (value.StartsWith("\"") && value.EndsWith("\""))
                {
                    bodyObj.Add(key, value.Replace("\"", String.Empty));
                }
                else if (value.StartsWith("{"))
                {
                    var dictJsonObj = JsonConvert.DeserializeObject<Dictionary<string, string>>(value);
                    Dictionary<string, object> dictObj = new Dictionary<string, object>();
                    bodyObj[key] = Deserialize(dictJsonObj);
                }
                else
                {
                    bodyObj[key] = value;
                }
            }
            return bodyObj;
        }
    }
}
