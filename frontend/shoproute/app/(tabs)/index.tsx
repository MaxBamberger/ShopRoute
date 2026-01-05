import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  TextInput, 
  TouchableOpacity, 
  StyleSheet, 
  Alert, 
  ScrollView, 
  KeyboardAvoidingView, 
  Platform,
  TouchableWithoutFeedback,
  Keyboard
} from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { useRouter } from 'expo-router';
import axios from 'axios';

interface Store {
  store_id: number;
  name: string;
  chain: string;
}

export default function ItemInput() {
  const [items, setItems] = useState('');
  const [selectedStore, setSelectedStore] = useState('');
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    fetchStores();
  }, []);

  const fetchStores = async () => {
    try {
      // For now, we'll hardcode the stores since we don't have a list endpoint
      const storeList = [
        { store_id: 1, name: 'Wegmans', chain: 'Wegmans' },
        { store_id: 2, name: 'ShopRite of West Caldwell', chain: 'ShopRite' },
        { store_id: 3, name: "Trader Joe's", chain: "Trader Joe's" }
      ];
      setStores(storeList);
      setSelectedStore(storeList[0].name); // Set first store as default
    } catch (error) {
      console.error('Failed to fetch stores:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOrganize = async () => {
    if (!items.trim()) {
      Alert.alert('Error', 'Please enter some grocery items');
      return;
    }
    
    if (!selectedStore) {
      Alert.alert('Error', 'Please select a store');
      return;
    }

    // Find the store_id for the selected store
    const store = stores.find(s => s.name === selectedStore);
    if (!store) {
      Alert.alert('Error', 'Invalid store selection');
      return;
    }

    router.push({
      pathname: '/shopping-list',
      params: { 
        items: items.trim(),
        store_id: store.store_id,
        store_name: store.name
      }
    });
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container} 
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
        <ScrollView 
          contentContainerStyle={styles.scrollContainer}
          keyboardShouldPersistTaps="handled"
        >
          <Text style={styles.title}>ShopRoute</Text>
          <Text style={styles.subtitle}>Enter your grocery items</Text>
          
          <TextInput
            style={styles.input}
            placeholder="milk, bread, bananas, eggs..."
            value={items}
            onChangeText={setItems}
            multiline
            returnKeyType="done"
            blurOnSubmit={true}
          />

          <Text style={styles.label}>Select Store:</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={selectedStore}
              onValueChange={(itemValue) => {
                console.log('Store selected:', itemValue);
                setSelectedStore(itemValue);
              }}
              style={styles.picker}
              itemStyle={styles.pickerItem}
              mode="dropdown"
            >
              {stores.map((store) => (
                <Picker.Item 
                  key={store.store_id} 
                  label={store.name} 
                  value={store.name}
                  color="#333"
                />
              ))}
            </Picker>
          </View>
          
          {/* Debug info - remove this later */}
          <Text style={styles.debugText}>Selected: {selectedStore}</Text>
          
          <TouchableOpacity 
            style={styles.button} 
            onPress={handleOrganize}
            activeOpacity={0.8}
          >
            <Text style={styles.buttonText}>Organize List</Text>
          </TouchableOpacity>
        </ScrollView>
      </TouchableWithoutFeedback>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  scrollContainer: {
    flexGrow: 1,
    padding: 20,
    justifyContent: 'center',
    minHeight: '100%',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 10,
    color: '#2e7d32',
  },
  subtitle: {
    fontSize: 18,
    textAlign: 'center',
    marginBottom: 30,
    color: '#666',
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 15,
    fontSize: 16,
    minHeight: 100,
    textAlignVertical: 'top',
    marginBottom: 20,
    backgroundColor: '#fff',
  },
  label: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    marginBottom: 30,
    backgroundColor: '#fff',
    ...Platform.select({
      ios: {
        height: 200,
      },
      android: {
        height: 50,
      },
    }),
  },
  picker: {
    height: '100%',
    width: '100%',
  },
  pickerItem: {
    fontSize: 16,
    height: 200,
  },
  button: {
    backgroundColor: '#2e7d32',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 10,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  debugText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 10,
    fontStyle: 'italic',
  },
  buttonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
});
