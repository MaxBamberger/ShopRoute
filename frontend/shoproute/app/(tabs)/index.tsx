import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';
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
      setSelectedStore('Wegmans'); // Default selection
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
    <View style={styles.container}>
      <Text style={styles.title}>ShopRoute</Text>
      <Text style={styles.subtitle}>Enter your grocery items</Text>
      
      <TextInput
        style={styles.input}
        placeholder="milk, bread, bananas, eggs..."
        value={items}
        onChangeText={setItems}
        multiline
      />

      <Text style={styles.label}>Select Store:</Text>
      <View style={styles.pickerContainer}>
        <Picker
          selectedValue={selectedStore}
          onValueChange={setSelectedStore}
          style={styles.picker}
        >
          {stores.map((store) => (
            <Picker.Item 
              key={store.store_id} 
              label={store.name} 
              value={store.name} 
            />
          ))}
        </Picker>
      </View>
      
      <TouchableOpacity style={styles.button} onPress={handleOrganize}>
        <Text style={styles.buttonText}>Organize List</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#fff',
    justifyContent: 'center',
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
    marginBottom: 20,
  },
  picker: {
    height: 50,
  },
  button: {
    backgroundColor: '#2e7d32',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
});
