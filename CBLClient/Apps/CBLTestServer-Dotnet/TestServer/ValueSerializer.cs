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
            else if (t.Equals(typeof(bool)))
            {
                Boolean item = Convert.ToBoolean(value);
                return item ? "true" : "false";
            }
            else if (t.Equals(typeof(string)))
            {
                return "\"" + value.ToString() + "\"";
            }
            else if (t.Equals(typeof(int)) || t.Equals(typeof(uint)))
            {
                return "I" + value;
            }
            else if (t.Equals(typeof(long)) || t.Equals(typeof(ulong)))
            {
                return "L" + value;
            }
            else if (t.Equals(typeof(float)))
            {
                return "F" + value;
            }
            else if (t.Equals(typeof(Dictionary<,>)))
            {
                Dictionary<string, object> dictionary = (Dictionary<string, object>) value;
                Dictionary<string, string> stringMap = new Dictionary<string, string>();
                foreach (string key in dictionary.Keys)
                {
                    stringMap[key] = Serialize(dictionary[key], dictionary[key].GetType());
                }
                return JsonConvert.SerializeObject(stringMap);
            }
            else if (t.Equals(typeof(List<>)))
            {
                List<object> list = (List<object>) value; 
                List<string> stringList = new List<string>();
                
                foreach (var item in list)
                {
                    stringList.Add(Serialize(item, item.GetType()));
                }
                return JsonConvert.SerializeObject(stringList);
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
                else if (value.StartsWith("["))
                {
                    var listJsonObj = JsonConvert.DeserializeObject<List<string>>(value);
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
